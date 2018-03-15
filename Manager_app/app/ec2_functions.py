from flask import render_template, redirect, url_for, request, flash
from app import webapp
import boto3
from app import config
from datetime import datetime, timedelta
from operator import itemgetter
from app.db_config import *
import manager
from User import User
from Photo import Photo
message = ''
warning = ''


def set_msg(msg_to_set):
    global message
    message = msg_to_set


def read_message():
    global message
    to_return = message
    message = ''
    return to_return


def set_warn(msg_to_set):
    global warning
    warning = msg_to_set


def read_warn():
    global warning
    to_return = warning
    warning = ''
    return to_return

def purge_S3(bucket_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)

    for obj in bucket.objects.all():
        s3.Object(bucket.name, obj.key).delete()

def purge_DB():
    User.query.delete()
    Photo.query.delete()
    db.session.commit()


def delete_all_data():
    purge_DB()
    purge_S3(IMAGE_STORE)

@webapp.route('/',methods=['GET'])
@webapp.route('/ec2_main',methods=['GET'])
# Display an HTML list all ec2 function provided by this application
def ec2_main():
    return render_template("ec2_functions/ec2_main.html",title="EC2 Instances Control")


@webapp.route('/ec2_add_instance',methods=['GET','POST'])
# A page for confirming adding an instance
def ec2_add_instance():
    return render_template("ec2_functions/ec2_add_instance.html",title="Adding an instance")


@webapp.route('/ec2_remove_instance',methods=['GET','POST'])
# A page for confirming resetting database
def ec2_remove_instance():
    return render_template("ec2_functions/ec2_remove_instance.html",title="Removing an instance")


@webapp.route('/ec2_remove_instance_select',methods=['GET','POST'])
# A page for selecting to remove an instance
def ec2_remove_instance_select():
    ec2 = boto3.resource('ec2')
    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    instances = ec2.instances.filter(Filters=filters)

    # Only show the user instances
    instances_filtered = [x for x in instances if x.image_id==config.ami_id]

    return render_template("ec2_functions/ec2_remove_instance_select.html",title="Removing an instance (Selectable)", instances=instances_filtered)


@webapp.route('/ec2_autoscaling',methods=['GET','POST'])
# A page for configuring auto-scaling
def ec2_autoscaling():
    if request.method == 'POST':
        Threshold_Growth = int(request.form['Threshold_Growth'])
        Threshold_Shrink = int(request.form['Threshold_Shrink'])
        Ratio_Growth = int(request.form['Ratio_Growth'])
        Ratio_Shrink = int(request.form['Ratio_Shrink'])
        push_autoscaling_params(low_thresh=Threshold_Shrink, high_thresh=Threshold_Growth,
                                down_factor=Ratio_Shrink, up_factor=Ratio_Growth)

        msg = "New auto-scaling config has been set."
        return render_template("ec2_functions/ec2_main.html", msg=msg, title="EC2 Instances Control")

    auto_scaling_params = [int(x) for x in fetch_autoscaling_params()]  # params are returned as floats
    return render_template("ec2_functions/ec2_autoscaling.html", title="Auto-Scaling Configuration",
                           params=auto_scaling_params)


@webapp.route('/ec2_reset',methods=['POST'])
# A page for confirming resetting database
def ec2_reset():
    error = delete_all_data()
    if error:
        return render_template('ec2_functions/ec2_main.html', error='MySQL server not running')
    else:
        return render_template('ec2_functions/ec2_main.html', msg='Removed all data')


@webapp.route('/ec2_remove_random/',methods=['POST'])
# Terminate a EC2 instance randomly
def ec2_remove_random():
    removed_id = manager.remove_worker_from_elb(1)
    if removed_id:
        set_msg("Instace %s has been removed." % removed_id)
        return redirect(url_for('ec2_list'))
    else:
        set_warn("Instance cannot be removed since there is only 1 instance now. If you are removing pending "
                 "instances, wait until it's running")
        return redirect(url_for('ec2_list'))


@webapp.route('/ec2_remove/<id>',methods=['POST'])
# Terminate a EC2 instance
def ec2_remove(id):
    # create connection to ec2 and elb
    ec2 = boto3.resource('ec2')
    myelb = boto3.client('elb')

    filters = [{'Name': 'instance-state-name', 'Values': ['running']}]
    instances = ec2.instances.filter(Filters=filters)

    # Only show the user instances
    instances_filtered = [x for x in instances if x.image_id==config.ami_id]

    if(instance for instance in instances_filtered if instance.id == id):
        if ( sum(1 for instance in instances_filtered) > 1):
            myelb.deregister_instances_from_load_balancer(LoadBalancerName='myelb',
                Instances=[{'InstanceId': id}])
            ec2.instances.filter(InstanceIds=[id]).terminate()
            msg = "Instace %s has been removed." %id
            set_msg(msg)
            return redirect(url_for('ec2_list'))

        else:
            set_warn("Instance cannot be removed since there is only 1 instance now.")
            return redirect(url_for('ec2_list'))

    return redirect(url_for('ec2_remove_instance'))


@webapp.route('/ec2_functions/create',methods=['POST'])
# Start a new EC2 instance
def ec2_create():
    new_id = manager.add_instance_with_elb(1)
    if new_id:
        set_msg("Created instance with ID: %s" % new_id[0])
        return redirect(url_for('ec2_list'))
    else:
        set_warn('Creation failed')
        return redirect(url_for('ec2_list'))


@webapp.route('/ec2_functions',methods=['GET'])
# Display an HTML list of all ec2 instances
def ec2_list():
    msg = read_message()
    warn = read_warn()
    return render_template("ec2_functions/ec2_list.html",title="EC2 Instances",instances=get_user_instances(),
                           msg=msg, error=warn)


@webapp.route('/ec2_functions/<id>',methods=['GET'])
#Display details about a specific instance.
def ec2_view(id):
    ec2 = boto3.resource('ec2')

    instance = ec2.Instance(id)

    client = boto3.client('cloudwatch')

    metric_name = 'CPUUtilization'

    ##    CPUUtilization, NetworkIn, NetworkOut, NetworkPacketsIn,
    #    NetworkPacketsOut, DiskWriteBytes, DiskReadBytes, DiskWriteOps,
    #    DiskReadOps, CPUCreditBalance, CPUCreditUsage, StatusCheckFailed,
    #    StatusCheckFailed_Instance, StatusCheckFailed_System


    namespace = 'AWS/EC2'
    statistic = 'Average'                   # could be Sum,Maximum,Minimum,SampleCount,Average



    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    cpu_stats = []


    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        cpu_stats.append([time,point['Average']])

    cpu_stats = sorted(cpu_stats, key=itemgetter(0))


    statistic = 'Sum'  # could be Sum,Maximum,Minimum,SampleCount,Average

    network_in = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='NetworkIn',
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    net_in_stats = []

    for point in network_in['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        net_in_stats.append([time,point['Sum']])

    net_in_stats = sorted(net_in_stats, key=itemgetter(0))



    network_out = client.get_metric_statistics(
        Period=5 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='NetworkOut',
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )


    net_out_stats = []

    for point in network_out['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        net_out_stats.append([time,point['Sum']])

        net_out_stats = sorted(net_out_stats, key=itemgetter(0))


    return render_template("ec2_functions/ec2_view.html",title="Instance Info",
                           instance=instance,
                           cpu_stats=cpu_stats,
                           net_in_stats=net_in_stats,
                           net_out_stats=net_out_stats)


def push_autoscaling_params(low_thresh, high_thresh, down_factor, up_factor):
    rc.set(REDIS_KEY_LOW_THRESHOLD, float(low_thresh))
    rc.set(REDIS_KEY_HIGH_THRESHOLD, float(high_thresh))
    rc.set(REDIS_KEY_DOWN_SCALE_FACTOR, float(down_factor))
    rc.set(REDIS_KEY_UP_SCALE_FACTOR, float(up_factor))


def fetch_autoscaling_params():
    """ Fetches auto-scaling parameters from redis

    :return: low_thresh, high_thresh, down_scale, up_scale in floats
    """
    if not rc.get(REDIS_KEY_INIT):
        reset_redis_db()
    return float(rc.get(REDIS_KEY_LOW_THRESHOLD)), float(rc.get(REDIS_KEY_HIGH_THRESHOLD)), \
           float(rc.get(REDIS_KEY_DOWN_SCALE_FACTOR)), float(rc.get(REDIS_KEY_UP_SCALE_FACTOR))


def get_user_instances():

    # create connection to ec2
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(id)
    client = boto3.client('cloudwatch')
    metric_name = 'CPUUtilization'
    namespace = 'AWS/EC2'
    statistic = 'Average'

    instances = ec2.instances.all()
    # Only show the user instances
    instances_filtered = [x for x in instances if x.image_id==config.ami_id]

    for instance in instances_filtered:
        # Only check cpu info for running ones,
        # make checking faster
        if instance.state['Name'] == 'running':
            cpu = client.get_metric_statistics(
                Period=1 * 60,
                StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
                EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
                MetricName=metric_name,
                Namespace=namespace,  # Unit='Percent',
                Statistics=[statistic],
                Dimensions=[{'Name': 'InstanceId', 'Value': instance.id}]
            )

            Datapoints = cpu['Datapoints']
            if Datapoints != []:
                latest_stat = sorted(Datapoints, key=itemgetter('Timestamp'))[-1]
                instance.cpu = latest_stat['Average']
            else: # Not sure this will happen or not
                instance.cpu = "N/A"
        else: # No datapoints show for non-running ones
            instance.cpu = "N/A"
    return instances_filtered
