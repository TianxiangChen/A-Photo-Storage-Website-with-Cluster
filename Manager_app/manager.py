import boto3
import time
from app import config
from datetime import datetime, timedelta
from operator import itemgetter
from app.db_config import *  # redis connection
import atexit
from app.ELB_Utility import get_instance_states, get_elb_names

# should also import database info, here i just mannually type

# Config for EC2 and Monitoring
ec2 = boto3.resource('ec2')
cloudwatch = boto3.client('cloudwatch')
myelb = boto3.client('elb')
metric_name = 'CPUUtilization'
namespace = 'AWS/EC2'
statistic = 'Average'
elb_start_time = 0

def start_userUI_server():
    # start DB server
    db_server = ec2.Instance(config.db_server_instance_id)
    db_server.start()
    print("Starting up DB server...")
    db_server.wait_until_running()
    print("DB server is up")
    config_load_balancer()


def create_instances(num):
    print("Creating %d new instances" % num)

    instances = ec2.create_instances(ImageId=config.ami_id,
                                     MinCount=1,
                                     MaxCount=num,
                                     InstanceType=config.instance_type,
                                     Monitoring={'Enabled': True},
                                     IamInstanceProfile={'Name': config.iam_role},
                                     EbsOptimized=False,
                                     SecurityGroups=[config.secure_group]
                                     )
    return [x.id for x in instances]


''' This fuction creates an user instance with attaching to elb'''


def add_instance_with_elb(num_to_add=1):
    if num_to_add < 1:
        return

    # create instances
    instances = create_instances(num_to_add)
    wait(config.black_out_elb_addition_after_creation)
    # Attach the instance to elb
    for instance in instances:
        print("Adding [%s] to load balancer" % instance)
        elb_attach_list = myelb.register_instances_with_load_balancer(
            LoadBalancerName='myelb', Instances=[{'InstanceId': instance}])

        print("this is the startup instance: %s" % instance)
    return instances


def config_load_balancer():
    print("Configuring load balancer")
    balancers = myelb.describe_load_balancers()
    if not balancers:
        create_load_balancer()
    add_instance_with_elb(num_to_add=config.initial_instance_count)

    total_wait = 0
    wait(3, 'Wait until instances are added to the elb\n')
    # wait until the first one starts, this call gets the first status in the list
    while list(get_instance_states(instance_ids=get_elb_names()).values())[0] != 'InService':
        wait(config.interval, 'Waiting for new instance to be InService')
        total_wait += config.interval
    print("Total wait until instance in service:" + str(total_wait))

    config.black_out_after_volumn_increase = total_wait if 30 < total_wait < 80 else 60


def create_load_balancer():
    print("Creating a new load balancer")
    response = myelb.create_load_balancer(
        LoadBalancerName='myelb',
        Listeners=[
            {
                'Protocol': 'HTTP',
                'LoadBalancerPort': 80,
                'InstanceProtocol': 'HTTP',
                'InstancePort': 80,
            },
        ],
        AvailabilityZones=['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e'
                           ],
        SecurityGroups=['sg-d8e2dbaa']
    )

    health_check = myelb.configure_health_check(
        LoadBalancerName='myelb',
        HealthCheck={
            'Target': 'HTTP:80/signin',  # change for true webapp
            'Timeout': 2,
            'Interval': 5,
            'UnhealthyThreshold': 2,
            'HealthyThreshold': 2
        }
    )

    stickiness = myelb.create_lb_cookie_stickiness_policy(
        LoadBalancerName='myelb',
        PolicyName='stick',
        CookieExpirationPeriod=3600
    )

    attach_stickness = myelb.set_load_balancer_policies_of_listener(
        LoadBalancerName='myelb',
        LoadBalancerPort=80,
        PolicyNames=[
            'stick',
        ],
    )


def get_running_instances_with_AMI(ami):
    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    return [x for x in instances if x.image_id == ami]


def remove_all_workers():
    return remove_worker_from_elb(len(get_running_instances_with_AMI(config.ami_id)), force=True)


def remove_worker_from_elb(num_to_remove, force=False):
    """Removes a number of instances from ELB. The instances are terminated too.

    The reamovable instances are filtered with config's AMI id

    :param num_to_remove: if greater or equal to the running, just remove at most (num_of_instance - 1), leave one
    behind
    :return: the id of instances removed
    """
    # Retrieve all running instances
    removed_instances = []
    instances_filtered = get_running_instances_with_AMI(config.ami_id)

    if num_to_remove >= len(instances_filtered):
        if not force:
            num_to_remove = len(instances_filtered) - 1
        else:
            num_to_remove = len(instances_filtered)  # remove all instances if forced

    for _ in range(num_to_remove):
        instance_to_remove = instances_filtered.pop()
        print("Removing instance %s" % instance_to_remove.id)
        myelb.deregister_instances_from_load_balancer(LoadBalancerName='myelb',
                                                      Instances=[{'InstanceId': instance_to_remove.id}])
        ec2.instances.filter(InstanceIds=[instance_to_remove.id]).terminate()
        removed_instances.append(instance_to_remove.id)
    return removed_instances


def wait(seconds, reason=''):
    if reason:
        print('# ' + reason)
    time.sleep(seconds)

def fetch_autoscaling_params():
    if not rc.get(REDIS_KEY_INIT):
        reset_redis_db()
    return float(rc.get(REDIS_KEY_LOW_THRESHOLD)), float(rc.get(REDIS_KEY_HIGH_THRESHOLD)), \
           float(rc.get(REDIS_KEY_DOWN_SCALE_FACTOR)), float(rc.get(REDIS_KEY_UP_SCALE_FACTOR))

def run_loop():
    num_of_growth_instance = 0
    num_of_shrink_instance = 0
    num_of_instance = 0
    utilization = 0

    # wait for 60 seconds before starting autoscaling
    print("Start")

    while True:
        # Initilize variables
        wait(config.interval)
        print('-------------------------------------')
        # Filter to take the user instances
        running_instances = get_running_instances_with_AMI(config.ami_id)
        num_of_instance = len(running_instances)

        cpu = cloudwatch.get_metric_statistics(
            Period=60,
            StartTime=datetime.utcnow() - timedelta(seconds=120),
            EndTime=datetime.utcnow(),
            MetricName=metric_name,
            Namespace=namespace,  # Unit='Percent',
            Statistics=[statistic],
            Dimensions=[{'Name': 'ImageId', 'Value': config.ami_id}]
        )

        if cpu['Datapoints']:
            latest_stat = sorted(cpu['Datapoints'], key=itemgetter('Timestamp'))[-1]
            # latest_stat should contain three dictionnaries: timestamp,average and unit
            # print(latest_stat)
            utilization = latest_stat['Average']

        print("number of instance running: %s" % num_of_instance)
        print("Average utilization is: %s" % utilization)

        low_thresh, high_thresh, down_factor, up_factor = fetch_autoscaling_params()
        print(" - Low: %s \n - High: %s\n - Down fac: %s\n - Up fac: %s" % (low_thresh, high_thresh, down_factor,up_factor))

        if utilization > high_thresh:
            # Exceed growth threshold, add instances
            if up_factor != 1:
                num_of_growth_instance = num_of_instance * (up_factor - 1)

            print("Attempt to increase worker pool")
            # Check the the num_of_growth_instance, there is cases if it is 0
            # then do not increase instances (e.g, growth ratio = 1)
            if num_of_growth_instance != 0:
                print("increase instance by %d" % num_of_growth_instance)
                add_instance_with_elb(int(num_of_growth_instance))
                # wait until the newly launched instances are up and running, or the large numebr of idle machines
                # could lead to the fluctuation of workers
                wait(config.black_out_after_volumn_increase,
                     'Sleep %ds after instance creation' % config.black_out_after_volumn_increase)

        if utilization < low_thresh:  # Below shrink threshold, remove instances
            if down_factor != 1 and num_of_instance != 0:  # Poetential to shrink the worker pool
                num_of_instance_after_shrink = int(num_of_instance / down_factor)
                if num_of_instance_after_shrink == 0:
                    num_of_instance_after_shrink = 1
                num_of_shrink_instance = num_of_instance - num_of_instance_after_shrink

            if num_of_shrink_instance:
                print("Shrink instances by %d" % num_of_shrink_instance)
                remove_worker_from_elb(num_of_shrink_instance)
                # wait until the newly launched instances are done, or the large numebr of idle machines
                # could lead to the fluctuation of workers
                wait(config.black_out_after_volumn_decrease,
                     'Sleep %ds after instance deletion' % config.black_out_after_volumn_decrease)

if __name__ == '__main__':
    remove_all_workers()
    atexit.register(remove_all_workers)
    start_userUI_server()
    run_loop()

