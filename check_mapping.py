
"""check_mapping.py — shows the current field structure of your index."""
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

COLLECTION_ENDPOINT = "orwbrix3dyknur9wqbcd.eu-north-1.aoss.amazonaws.com"
REGION = "eu-north-1"
INDEX_NAME = "rag-chunks"

credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, REGION, "aoss")

client = OpenSearch(
    hosts=[{"host": COLLECTION_ENDPOINT, "port": 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=60,
    max_retries=3,
    retry_on_timeout=True,
)

mapping = client.indices.get_mapping(index=INDEX_NAME)
import json
print(json.dumps(mapping, indent=2))
