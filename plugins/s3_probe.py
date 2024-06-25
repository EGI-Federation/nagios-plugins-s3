#!/usr/bin/env python3
##############################################################################
# DESCRIPTION
##############################################################################

"""
EGI S3 Storage probe

"""

import datetime
import filecmp
import shutil
import sys
import tempfile
import time
import uuid
import boto3
import botocore
import nap.core

PROBE_VERSION = "v0.0.1"


# ########################################################################### #
app = nap.core.Plugin(description="NAGIOS S3 probe", version=PROBE_VERSION)
app.add_argument("-E", "--endpoint", help="base URL to test")

app.add_argument("-accesskey", "--s3-access-key", help="S3 access key")
app.add_argument("-secretkey", "--s3-secret-key", help="S3 secret key")
app.add_argument("-region", "--s3-region", help="S3 region")
app.add_argument("-bucket", "--s3-bucket", help="S3 bucket")

app.add_argument(
    "--se-timeout",
    dest="se_timeout",
    type=int,
    help="storage operations timeout",
    default=60,
)

app.add_argument("-RO", "--read-only", dest="read_only", action="store_true",
     help="enable read-only tests")

# Service version(s)
workdir_metric = tempfile.mkdtemp()

# files and patterns
_fileTest = workdir_metric + "/testFile.txt"
_fileTestIn = workdir_metric + "/testFileIn.txt"
_filePattern = "testfile-put-%s-%s.txt"  # time, uuid
_fileDictionary = {}

def parse_args(args, io):
    if args.s3_access_key and args.s3_secret_key and args.s3_bucket:
        app.s3_resource = boto3.resource('s3',
            endpoint_url=args.endpoint,
            aws_access_key_id=args.s3_access_key,
            aws_secret_access_key=args.s3_secret_key,
            aws_session_token=None,
            config=boto3.session.Config(signature_version='s3v4'),
            verify=True)
        app.s3_target = boto3.client('s3',
            endpoint_url=args.endpoint,
            aws_access_key_id=args.s3_access_key,
            aws_secret_access_key=args.s3_secret_key,
            aws_session_token=None,
            config=boto3.session.Config(signature_version='s3v4'),
            verify=True)
        app.s3_bucket_name = args.s3_bucket
    else:
        return 1

@app.metric(seq=1, metric_name="LsBucket", passive=True)
def metricLsBucket(args, io):
    """
    List available buckets.
    """
    if parse_args(args, io):
        io.status = nap.CRITICAL
        io.summary = "Argument Endpoint (-E, --endpoint) is missing"
        return
    try:
        response = app.s3_target.list_buckets()
        io.summary = "Buckets successfully listed"
        io.status = nap.OK
    except Exception as e:
        io.set_status(
            nap.CRITICAL,
            "problem invoking s3.list_bucket(): %s:%s" % (str(e), sys.exc_info()[0]),
        )


@app.metric(seq=2, metric_name="Put", passive=True)
def metricPut(args, io):
    """Copy a local file to s3 path."""

    # verify lsdir test succeeded
    results = app.metric_results()
    if results[0][1] != nap.OK:
        io.set_status(nap.WARNING, "lsdir skipped")
        return
    if args.read_only:
        io.set_status(nap.OK, "read-only endpoint")
        return

    # generate source file
    try:
        src_file = _fileTest
        fp = open(src_file, "w")
        for s in "1234567890":
            fp.write(s + "\n")
        fp.close()

        fn = _filePattern % (str(int(time.time())), str(uuid.uuid1()))

        _fileDictionary[args.endpoint] = {}
        _fileDictionary[args.endpoint]["fn"] = fn
    except IOError:
        io.set_status(nap.CRITICAL, "Error creating source file")

    # Set transfer parameters

    stMsg = "File was copied to the S3 endpoint"

    try:
        app.s3_target.upload_file(src_file, app.s3_bucket_name, fn)
        io.summary = stMsg
        io.status = nap.OK
    except Exception as e:
        io.set_status(
            nap.CRITICAL,
            "problem invoking upload file(): %s:%s" % (str(e), sys.exc_info()[0]),
        )


@app.metric(seq=3, metric_name="Get", passive=True)
def metricGet(args, io):
    """Copy given remote file(s) from the storage to a local file."""

    # verify previous test succeeded
    results = app.metric_results()
    if results[1][1] != nap.OK:
        io.set_status(nap.WARNING, "Get skipped")
        return
    if args.read_only:
        io.set_status(nap.OK, "read-only endpoint")
        return

    if len(_fileDictionary.keys()) == 0:
        io.set_status(nap.WARNING, "No endpoints found to test")
        return

    for endpt in _fileDictionary.keys():

        src_filename = (_fileDictionary[endpt])["fn"]

        dest_file =  _fileTestIn
        stMsg = "File was copied from the S3 Storage."
        try:
            app.s3_resource.Bucket(app.s3_bucket_name).download_file(src_filename,dest_file)
            io.summary = stMsg
            io.status = nap.OK
        except Exception as e:
            io.set_status(
                nap.CRITICAL,
                "problem invoking download_file(): %s:%s"
                % (str(e), sys.exc_info()[0]),
            )


@app.metric(seq=4, metric_name="Del", passive=True)
def metricDel(args, io):
    """Delete given file(s) from the storage."""

    # skip only if the put failed
    results = app.metric_results()
    if results[2][1] != nap.OK:
        io.set_status(nap.WARNING, "Del skipped")
        return
    if args.read_only:
        io.set_status(nap.OK, "read-only endpoint")
        return

    if len(_fileDictionary.keys()) == 0:
        io.set_status(nap.CRITICAL, "No endpoints found to test")

    for endpt in _fileDictionary.keys():

        src_filename = (_fileDictionary[endpt])["fn"]
        stMsg = "File was deleted from the S3 storage endpoint."
        try:
            app.s3_resource.Object(app.s3_bucket_name, src_filename).delete()
            io.status = nap.OK
            io.summary = stMsg
        except Exception as e:
            io.set_status(
                nap.CRITICAL,
                "problem invoking delete(): %s:%s" % (str(e), sys.exc_info()[0]),
            )


@app.metric(seq=5, metric_name="All", passive=False)
def metricAlll(args, io):
    """Active metric to combine the result from the previous passive ones"""

    results = app.metric_results()

    statuses = [e[1] for e in results]

    if all(st == 0 for st in statuses):
        io.set_status(nap.OK, "All fine")
    elif nap.CRITICAL in statuses:
        io.set_status(nap.CRITICAL, "Critical error executing tests")
    else:
        io.set_status(nap.WARNING, "Some of the tests returned a warning")

    try:
        shutil.rmtree(workdir_metric)
    except OSError:
        pass


if __name__ == "__main__":
    app.run()
