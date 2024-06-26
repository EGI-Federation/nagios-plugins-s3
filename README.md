# Nagios-plugins-s3

This is Nagios probe to monitor S3 Storage endpoints executing simple file operations

It's based on the boto3 library for the storage operations and the python-nap library for execution and reporting.

The probes runs the following passive checks in sequence:

* LsBuckets: list the buckets at th eendpoint
* Put: put a test file
* Get: copy the file locally and check if content matches
* Del: delete the file

the active check 'all' just combines the passive checks outcomes.

## Usage

```shell
usage: s3_probe.py [-h] [--version] [-H HOSTNAME] [-w WARNING] [-c CRITICAL] [-d] [--print-all] [-p PREFIX] [-s SUFFIX] [-t TIMEOUT] [-C COMMAND] [--dry-run] [-o OUTPUT] [-E ENDPOINT] [-accesskey S3_ACCESS_KEY]
                   [-secretkey S3_SECRET_KEY] [-region S3_REGION] [-bucket S3_BUCKET] [--se-timeout SE_TIMEOUT] [-RO]

NAGIOS S3 probe

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -H HOSTNAME, --hostname HOSTNAME
                        Host name, IP Address, or unix socket (must be an absolute path)
  -w WARNING, --warning WARNING
                        Offset to result in warning status
  -c CRITICAL, --critical CRITICAL
                        Offset to result in critical status
  -d, --debug           Specify debugging mode
  --print-all           Print output from all metrics to stdout
  -p PREFIX, --prefix PREFIX
                        Text to prepend to ever metric name
  -s SUFFIX, --suffix SUFFIX
                        Text to append to every metric name
  -t TIMEOUT, --timeout TIMEOUT
                        Global timeout for plugin execution
  -C COMMAND, --command COMMAND
                        Nagios command pipe for submitting passive results
  --dry-run             Dry run, will not execute commands and submit passive results
  -o OUTPUT, --output OUTPUT
                        Plugin output format; valid options are nagios, check_mk or passive (via command pipe); defaults to nagios)
  -E ENDPOINT, --endpoint ENDPOINT
                        base URL to test
  -accesskey S3_ACCESS_KEY, --s3-access-key S3_ACCESS_KEY
                        S3 access key
  -secretkey S3_SECRET_KEY, --s3-secret-key S3_SECRET_KEY
                        S3 secret key
  -region S3_REGION, --s3-region S3_REGION
                        S3 region
  -bucket S3_BUCKET, --s3-bucket S3_BUCKET
                        S3 bucket
  --se-timeout SE_TIMEOUT
                        storage operations timeout
  -RO, --read-only      enable read-only tests
```

## Example

```shell
/plugins/s3_probe.py  -d -E https://S3_endpoint -bucket <bucket> -accesskey <accesskey> -secretkey <secretkey>

#To build
make rpm
```

