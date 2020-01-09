# Debugging

## GDB

1. Set environment variables for the environment to be debugged.
2. Spin up associated docker container for dynalite if required, `docker-compose up dynalite`.  If you are debugging against AWS DynamoDB itself be sure to setup your AWS Credentials accordingly.
3. Install packages: `sudo pip install -r src/app_requirements.txt`
4. Set the PYTHONPATH for gdb: `export PYTHONPATH=/opt/subhub/src/:PYTHONPATH`
5. Start gdb: `gdb python3.7`
6. Run the application of choise: `run APPLICATION`

Where APPLICATION is either
* `src/hub/app.py`
