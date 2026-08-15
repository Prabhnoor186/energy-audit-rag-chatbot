# Energy Audit RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot for querying energy audit reports from a mechanical engineering internship. It retrieves relevant report sections and generates grounded answers with source citations instead of relying solely on an LLM's general knowledge.

## What It Does

- Ingests compressor and boiler energy audit reports from a 21-day monitoring study.
- Splits documents into coherent sections, generates embeddings, and stores them in a vector database.
- For each question, retrieves the most relevant sections using semantic similarity.
- Generates an answer using the retrieved context and displays the supporting sources.
- Declines to answer when the requested information is outside the source documents rather than hallucinating an answer.

## Tech Stack

`AWS Bedrock (Titan Embeddings V2, Amazon Nova Micro)` · `OpenSearch Serverless (NextGen)` · `AWS Lambda` · `API Gateway` · `Terraform` · `Streamlit` · `Python`

## Demo

<video src="https://github.com/Prabhnoor186/energy-audit-rag-chatbot/raw/main/Energy_Audit_Chatbot_demo.mp4.mp4" controls width="700">
  Your browser doesn't support embedded video — <a href="https://github.com/Prabhnoor186/energy-audit-rag-chatbot/raw/main/Energy_Audit_Chatbot_demo.mp4.mp4">watch it here</a>.
</video>

Example questions:

- "What is the rated power of the compressor?"
- "What methodology was used for the audits?"
- "What fuel does the boiler use?"
- "What is the price of a new industrial boiler?" — Out of scope; the chatbot correctly states that this information is not available in the source documents.

## Architecture

### One-Time Setup

Audit reports (DOCX/PPTX) → section-based chunking → 69 document chunks → Titan Embeddings V2 → 1024-dimensional vectors → OpenSearch Serverless

### Live Query Flow

Streamlit UI → API Gateway → Lambda → Bedrock embedding → OpenSearch k-NN search → retrieved context → Amazon Nova Micro → grounded answer with source citations

## Why These Technologies?

- **OpenSearch Serverless NextGen:** Chosen over Classic because Classic requires minimum OCU capacity even when idle. NextGen is designed to scale down when inactive, making it better suited to an intermittent demo and development workload. At the time of this project, the AWS Terraform provider did not support creating NextGen collections directly, so the collection is created through AWS CLI while Terraform manages the surrounding infrastructure.
- **Amazon Nova Micro:** Used as the generation model because it provides a lightweight option for generating responses from retrieved context through Amazon Bedrock.
- **Section-Based Chunking:** Documents are split at section boundaries instead of arbitrary character or token limits. This keeps related information together and improves retrieval quality.
- **Ephemeral Infrastructure:** The infrastructure is designed to be deployed for testing or demonstrations and destroyed afterward using `terraform destroy` and the relevant AWS CLI commands.

## CI/CD

GitHub Actions uses two separate workflows:

- **`ci.yml`** — Runs automatically on pushes and pull requests to `main`. It validates Terraform, lints Python, and builds the Lambda deployment package as a downloadable artifact. It does not deploy anything to AWS.
- **`deploy.yml`** — Runs only through `workflow_dispatch` and requires an explicit confirmation. It applies the Terraform configuration and deploys the AWS infrastructure.

The deployment workflow is intentionally manual because the infrastructure is designed to be ephemeral rather than permanently running.

## Project Structure

```text
.
├── .github/workflows/       # CI and manual CD workflows
├── main.tf                  # Terraform infrastructure
├── lambda_function.py       # Embedding, retrieval, and generation logic
├── app.py                   # Streamlit chat interface
├── chunk_docx.py            # Extracts and chunks source documents
├── create_index.py          # Creates the OpenSearch vector index
├── embed_and_upload.py      # Embeds chunks and uploads them to OpenSearch
├── test_query.py            # Retrieval-only test
├── chunks.json              # 69 processed document chunks
└── architecture.svg         # Architecture diagram
```

## Running Locally

### Prerequisites

You need an AWS account with access to Amazon Bedrock and OpenSearch Serverless in a supported region, along with appropriately configured AWS credentials.

### 1. Deploy the Terraform Resources

```bash
terraform init
terraform apply
```

### 2. Create the OpenSearch NextGen Collection

```bash
aws opensearchserverless create-collection-group \
  --name rag-chatbot-group \
  --standby-replicas DISABLED \
  --region <region>

aws opensearchserverless create-collection \
  --name rag-chatbot \
  --type VECTORSEARCH \
  --collection-group-name rag-chatbot-group \
  --standby-replicas DISABLED \
  --region <region>
```

### 3. Create the Index and Upload the Data

```bash
python create_index.py
python embed_and_upload.py
```

### 4. Start the Streamlit Application

```bash
python -m streamlit run app.py
```

## Teardown

When the infrastructure is no longer needed:

```bash
terraform destroy

aws opensearchserverless delete-collection \
  --name rag-chatbot \
  --region <region>

aws opensearchserverless delete-collection-group \
  --name rag-chatbot-group \
  --region <region>
```

## Data Note

The source documents are energy audit reports authored during a mechanical engineering internship. Before being used in this project, the documents were reviewed to remove client-identifying information, including company names, facility addresses, and client contact details.
