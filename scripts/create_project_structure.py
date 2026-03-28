import os

# List of directories to create for project structure
directories = [
    'logs',
    'services',
    'requirements',
    'docker',
    'env',
    'docs'
]

# Create directories
for directory in directories:
    os.makedirs(directory, exist_ok=True)

# Create a logging configuration file
with open('logging_config.py', 'w') as log_file:
    log_file.write("""# Logging configuration\nimport logging\n\ndef setup_logging(log_file='app.log'):\n    logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')\n""")

# Create requirements.txt
with open('requirements.txt', 'w') as req_file:
    req_file.write("""# Add your project requirements here\n\n# Example: requests\nrequests\n""")

# Create Dockerfile
with open('docker/Dockerfile', 'w') as docker_file:
    docker_file.write("""# Dockerfile for Project\nFROM python:3.8-slim\nWORKDIR /usr/src/app\nCOPY requirements.txt ./\nRUN pip install --no-cache-dir -r requirements.txt\nCOPY . .\nCMD [ 'python', 'app.py' ]\n""")

# Create environment file
with open('.env', 'w') as env_file:
    env_file.write("""# Environment Variables\n# Example: DEBUG=True\nDEBUG=False\n""")

# Create documentation structure
with open('docs/README.md', 'w') as doc_file:
    doc_file.write("""# Documentation\nThis project is structured to include logging, services, requirements, and Docker configuration.\n""")
