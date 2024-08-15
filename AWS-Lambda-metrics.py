import argparse
import boto3
import csv
from datetime import datetime, timedelta, timezone
from io import StringIO


class ListVpcPrivatelinks:
    def __init__(self):
        self._parse_args()
        self.metric_csv = 'aws_privatelinks.csv'
        self.end_time = datetime.now(timezone.utc)
        self.start_time = datetime(
            self.end_time.year, self.end_time.month, self.end_time.day
        ) - timedelta(days=self.args.days)
        self.period = 86400
        # self.s3_bucket = self.args.bucket
        # self.s3_client = boto3.client("s3")
        # self.s3_object_key = f"{self.args.region}/{self.end_time.year}/{self.end_time.month}/{self.end_time.day}/vpc_privatelinks_data_{self.end_time.strftime('%Y%m%d')}.csv"
        self.ec2_client = boto3.client("ec2", self.args.region)
        self.ec2_response = self.ec2_client.describe_vpc_endpoints()
        self.cloudwatch_client = boto3.client("cloudwatch", self.args.region)
        self.cloudwatch_response = self.cloudwatch_client.list_metrics(
            Namespace="AWS/PrivateLinkEndpoints", MetricName="BytesProcessed"
        )
        self.dimension_template = {
            "VPC Id",
            "VPC Endpoint Id",
            "Endpoint Type",
            "Service Name",
        }
        self.outputs = []

    def _parse_args(self):
        parser = argparse.ArgumentParser(
            description="List VPC Privatelinks and upload data to S3."
        )
        parser.add_argument(
            "--days",
            "-d",
            type=int,
            help="Number of days to query [default=1]",
            default=1,
        )
        parser.add_argument(
            "--region", "-r", help="AWS region name [required]", required=True
        )
        # parser.add_argument(
        #    "--bucket", "-b", help="S3 bucket name [required]", required=True
        # )

        self.args = parser.parse_args()

    def _list_endpoints(self):
        self.endpoints = []
        for endpoint in self.ec2_response["VpcEndpoints"]:
            try:
                endpoint_name = [
                    tag["Value"] for tag in endpoint["Tags"] if tag["Key"] == "Name"
                ][0]
            except IndexError:
                endpoint_name = f'Unnamed_{endpoint["VpcEndpointId"]}'

            endpoint_data = {
                "Name": endpoint_name,
                "VpcEndpointId": endpoint["VpcEndpointId"],
                "VpcId": endpoint["VpcId"],
                "ServiceName": endpoint["ServiceName"],
                "State": endpoint["State"],
            }

            self.endpoints.append(endpoint_data)

    def _process_endpoint(self, endpoint):
        dimensions = []
        print("Name:", endpoint["Name"])
        print("Endpoint ID:", endpoint["VpcEndpointId"])
        print("VPC ID:", endpoint["VpcId"])
        print("Service Name:", endpoint["ServiceName"])
        print("State:", endpoint["State"])

        for metric in self.cloudwatch_response["Metrics"]:
            if {dim["Name"] for dim in metric["Dimensions"]} != self.dimension_template:
                continue
            if [
                dim["Value"]
                for dim in metric["Dimensions"]
                if dim["Name"] == "VPC Endpoint Id"
            ] != [endpoint["VpcEndpointId"]]:
                continue
            dimensions = metric["Dimensions"]

        if dimensions:
            cloudwatch_response_datapoints = (
                self.cloudwatch_client.get_metric_statistics(
                    Namespace="AWS/PrivateLinkEndpoints",
                    MetricName="BytesProcessed",
                    StartTime=self.start_time,
                    EndTime=self.end_time,
                    Period=self.period,
                    Statistics=["Sum"],
                    Dimensions=dimensions,
                )
            )

            if not cloudwatch_response_datapoints["Datapoints"]:
                print("No metric data available for this VPC endpoint.")
            for point in sorted(
                cloudwatch_response_datapoints["Datapoints"],
                key=lambda p: p["Timestamp"],
            ):
                ts1 = point["Timestamp"]
                ts2 = ts1 + timedelta(seconds=self.period)
                if ts2 > self.end_time:
                    continue
                out = dict(endpoint)
                out.update(
                    {
                        "From": ts1.timestamp(),
                        "To": ts2.timestamp(),
                        "BytesProcessed": point["Sum"],
                    }
                )

                self.outputs.append(out)
                print("Timestamp:", point["Timestamp"])
                print("Bytes Processed:", out["BytesProcessed"])
        else:
            print("No relevant dimensions found for this VPC endpoint.")

        print("------------------------------")

    def _create_csv(self):
        self.csv_buffer = StringIO()
        with open(self.metric_csv , 'w', newline = '') as file:
            writer = csv.DictWriter(file, fieldnames=self.outputs[0].keys())
            writer.writeheader()
            for endpoint in self.outputs:
                writer.writerow(endpoint)
    """
    def _upload_to_s3(self):
        print(f"Uploading data to S3 path s3://{self.s3_bucket}/{self.s3_object_key}")
        self.s3_client.put_object(
            Body=self.csv_buffer.getvalue(),
            Bucket=self.s3_bucket,
            Key=self.s3_object_key,
        )
        print("Data uploaded to S3 successfully.")
        print("------------------------------")
    """
    def run(self):
        self._list_endpoints()
        for endpoint in self.endpoints:
            self._process_endpoint(endpoint)
        if not self.outputs:
            print("No outputs collected for the selected period.")
            return
        self._create_csv()
        # self._upload_to_s3()


if __name__ == "__main__":
    ListVpcPrivatelinks().run()
