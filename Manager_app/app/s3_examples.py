from flask import render_template, redirect, url_for, request
from app import webapp

import boto3

@webapp.route('/s3_examples',methods=['GET'])
# Display an HTML list of all s3 buckets.
def s3_list():
    # Let's use Amazon S3
    s3 = boto3.resource('s3')

    # Print out bucket names
    buckets = s3.buckets.all()

    for b in buckets:
        name = b.name

    buckets = s3.buckets.all()

    return render_template("s3_examples/list.html",title="s3 Instances",buckets=buckets)


@webapp.route('/s3_examples/<id>',methods=['GET'])
#Display details about a specific bucket.
def s3_view(id):
    s3 = boto3.resource('s3')

    bucket = s3.Bucket(id)

    for key in bucket.objects.all():
        k = key

    keys =  bucket.objects.all()


    return render_template("s3_examples/view.html",title="S3 Bucket Contents",id=id,keys=keys)
