# FastAPI Project

A FastAPI-based project for querying and serving data from a relational database. You can run it locally using Docker or deploy it on Kubernetes using Minikube.

---

## 🚀 How to Use

## Step 1: Clone the project

```bash
git clone https://github.com/minhnn2002/fastapi.git
```

Then cd to the main project
```bash
cd fastapi
```

## Step 2: Create the virtual environment
Create the virtual enviroment
```bash
python -m venv .venv
source .venv/bin/activate    # On Linux/macOS
.\.venv\Scripts\activate     # On Windows
```

Then install the requirement packages:
```bash
pip install -r requirements.txt
```

## Step 3: Create the .env file
Create a file named .env in the root directory with the same content as env_example file (replace with your actual credentials). 

## Step 4: Run the project on Docker. (If you deploy on k8s, skip to the next step)
To run the project on Docker, simply run the command 
```bash
docker compose up -d
```

After it starts, open your browser and navigate to:
```bash
http://localhost:8000/docs
```
to access the interactive API documentation.

## Step 5: Deploy the project on K8S
Skip this step if you're only running with Docker.

### 1. Fill in the secrets file:
Edit k8s/secret.yaml with the same content as .env, but wrap every value with double quotes.

### 2. Start Minikube:
I'm using minikube to run so first start the minikube
```bash
minikube start --driver=docker
```

Then verify it's running:
```bash
minikube status
```

### 3. Deploy to the cluster:
If everything is fine, then move to the k8s folder:

```bash
cd .\k8s\
```

Deploy the minikube cluster:

```bash
kubectl apply -f ./.
```

Finally use the following command to create the service to connect to API:
```bash
minikube service fastapi-serivce
```
