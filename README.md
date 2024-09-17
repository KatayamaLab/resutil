# Resutil
Japanese readme is [here]([https://](https://github.com/KatayamaLab/resutil/blob/main/README.ja.md))

## What is Resutil

**Resutil** is a utility to manage experimental result data obtained from Python projects. It also manages dependency such as codes and input data with result data. Data is synced to the cloud for team sharing and collaboration.

## Why choose Resutil?

- **Simple**: Easy to install and can be quickly integrated into your project.  
- **High Reproducibility**: Tracks programs, input data, and experimental results.
- **Open-source and free**: Join development to future release of Resutil.


## Features

- Sync experimental data saved in a specific directory to the cloud (currently only for Box) after the program execution finished.
- Save information necessary to reproduce the experiment in a YAML file.
- Execution command
- Input files given as arguments (only files within folders managed by resutil)
- Git commit hash
- Uncommitted files
- Upload experimental data that hasn’t been uploaded yet.
- Download experimental data from the cloud using commands.
- Automatically download dependencies that do not existing at run time.

## Installation

Open terminal and run

```bash
pip install resutil
```

Get JWT (JSON Web Tokens) key from [Box](https://developer.box.com/guides/authentication/jwt/), and saved as `key.json`:

```JSON
{
  "boxAppSettings": {
    "clientID": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "appAuth": {
      "publicKeyID": "xxxxxxxx",
      "privateKey": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n-----END ENCRYPTED PRIVATE KEY-----\n",
      "passphrase": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  },
  "enterpriseID": "796607301"
}
```

Initialize resutil

```bash
$ cd your-project-root-directory
$ resutil init
Input project name (resutil): MyProj
Input directory name to store results (results): results
Do you want to add .gitignore to results? (Y/n): Y
Input storage_type (box): box
Input key file_path (key.json): key.json
Do you want to add key.json to .gitignore? (Y/n): Y
Input folder id of base dir: 123456789012
✅ Initialized.
```

The folder id is the Box folder ID, which is the numeric part of the URL when viewing the folder on Box (e.g., https://xxxx.app.box.com/folder/123456789012).

A file named `resutil-conf.yaml` will be created.

Modify main function in your project like:

```python

# Import resutil
import resutil

# Add decorator before the main function
@resutil.main()
def main_func(params):
    # A directory is automatically created, and its path is stored in params.ex_dir
    ex_dir = params.ex_dir 

    # Execute the program HERE🚀
    # Resutil will handle the rest

if __name__ == "__main__":
    main_func()
```

### Tips for Using argparse

Resutil uses the options `--resutil_comment` and `--resutil_no_interactive`. If you use argparse in the main code where you want to integrate Resutil, these options will cause an error as undefined arguments. Please use `parse_known_args()` instead of `parse_args()` as shown below.

```python
    parser = argparse.ArgumentParser("Your code")
    parser.add_argument("--arg1", type=str)
    parser.add_argument("arg2", type=str, help="test input")
    parsed_args, unknown = parser.parse_known_args()  # Use parse_known_args instead of parse_args
```

## Usage

Run the program integrated with Resutil. You will first be prompted for a comment, and then an experiment result directory will be automatically created. This directory will include a name composed of a sequential alphabet, date, time, and your comment. The directory is then zipped and uploaded to the specified cloud storage after the program finishes.

```bash
$ python sample.py

✨ Running your code with Resutil

📦 Connected to Google Cloud Storage
  📁 Bucket name: resutil
  📁 Project dir: your_project

📝 Input comment for this experiment (press [tab] key for completion): nice-comment

🔍 Unstaged files will be stored in the result dir:
  - README.ja.md
  - README.md
🚀 Running the main function...

### Your code's output

🗂️ Uploading: aapfup_20240704T191555_nice-comment
ℹ️ There are 9 other experiment directories that have not been uploaded.
✅ Done
```

## How to setup cloud storage for Resutil

Resutil supports Google Cloud Storage, Google Drive, and Box for a cloud storage to store result files. To connect these cloud services following setup will be required.

### Google Cloud Storage

1. **Create a Project**:
    - If you don't already have a project, go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. **Enable the Cloud Storage API**:
    - Go to the [API Library](https://console.cloud.google.com/apis/library) in the Google Cloud Console.
    - Search for "Cloud Storage" and enable the API for your project.
3. **Create a Storage Bucket**:
    - In the Google Cloud Console, go to the [Cloud Storage Browser](https://console.cloud.google.com/storage/browser).
    - Click on "Create Bucket."
    - Follow the prompts to name your bucket, select a storage class, and set the location for your bucket.
4. **Create a Service Account**:
    - In the Google Cloud Console, go to the [IAM & Admin](https://console.cloud.google.com/iam-admin/serviceaccounts) section.
    - Click on "Create Service Account."
    - Provide a name and description for the service account, and click "Create."
5. **Grant Permissions to the Service Account**:
    - Select the "Storage Object User" roles that grant the necessary permissions to the service account.
    - Click "Continue," and then "Done."
6. **Create and Download a Key for the Service Account**:
    - Click on the service account you just created.
    - Go to the "Keys" tab.
    - Click "Add Key," then "Create New Key."
    - Choose "JSON" as the key type, and click "Create." The key file will be downloaded to your computer.

### Google Drive

1. **Create a Folder in Google Drive**:
    - Open [Google Drive](https://drive.google.com/).
    - Click on "New" and select "Folder."
    - Name the folder and click "Create."
2. **Get the Folder ID**:
    - Navigate to the folder you just created.
    - The folder ID is the part of the URL after `folders/`. For example, in the URL `https://drive.google.com/drive/folders/1a2b3c4d5e6f`, the folder ID is `1a2b3c4d5e6f`.
3. **Create a Service Account**:
    - Go to the [Google Cloud Console](https://console.cloud.google.com/).
    - Select your project or create a new one.
    - Navigate to the [IAM & Admin](https://console.cloud.google.com/iam-admin/serviceaccounts) section.
    - Click "Create Service Account."
    - Provide a name and description for the service account, and click "Create."
4. **Create and Download a Key for the Service Account**:
    - Click on the service account you just created.
    - Go to the "Keys" tab.
    - Click "Add Key," then "Create New Key."
    - Choose "JSON" as the key type, and click "Create." The key file will be downloaded to your computer.
5. **Enable the Google Drive API**:
    - Go to the [API Library](https://console.cloud.google.com/apis/library) in the Google Cloud Console.
    - Search for "Google Drive API" and enable it for your project.
6. **Share the Folder**:
    - In Google Drive, right-click on the folder you created.
    - Select "Share."
    - In the "Share with people and groups" field, enter the email address of the service account (you can find this in the JSON key file under `client_email`).
    - Give the service account `Editor` access.
    - Click "Send."

### Box

Sure, I can guide you through the process of obtaining a JWT (JSON Web Token) from Box's developer console. Follow these steps:

1. **Create a Box Application**
    - Go to the [Box Developer Console](https://account.box.com/login) and log in with your Box account.
    - Click on "Create New App".
    - Give your app a name and click "Next".
    - Choose "Custom App" and select "Server Authentication (with JWT)".

2. **Configure Your Application**
    - In your app's settings, go to the "Configuration" tab.
    - Under "Application Scopes", choose two access levels, "Read/Write all files and folders stored in Box".
    - Scroll down to the "Add and Manage Public Keys" section and click "Generate a Public/Private Keypair". This will download a `.json` file containing your app's credentials.

3. **Create a Service Account**
    - In the "Authorization" tab, click on "Create Service Account".
    - Follow the prompts to create the service account. This account will be used to authenticate your app.

4. **Grant permissions to the service account**
    - Grant the service account “AutomationUser_xxxxx@boxdevedition.com” editor permissions for the folder you want to use.
    
## Commands

### `resutil init`

`resutil init` creates `resutil-conf.yaml` in your project folder such as:

```yaml
project_name: MyProj
results_dir: results/
storage_type: box
storage_config:
  base_folder_id: xxxx
  key_file: key.json
```

### `resutil push`

The `resutil push` command is used to upload experimental data to the cloud that does not exist in the cloud result directory.

`resutil push [exp_name]` uploads experiment a specific directory to the cloud. Depending directorys included in `exp-config.yaml` are automtically uploaded. `--no-dependency` option restrain automatic dependency upload.

`resutil pull` will upload all experimental data to the cloud.

This is useful for keeping your local data up-to-date with the data stored in the cloud, especially when multiple people are working on the same project and updating the experimental data.

### `resutil pull`

The `resutil pull` command is used to download a specific experimental data from the cloud that does not exist in the local result directory.

`resutil pull [exp_name]` downloads experiment directory from cloud. Depending directorys included in `exp-config.yaml` are automtically downlowded. `--no-dependency` option restrain automatic dependency download.

`resutil pull` will download all experimental data from the cloud that is not currently in your local result directory.

This is useful for keeping your local data up-to-date with the data stored in the cloud, especially when multiple people are working on the same project and updating the experimental data.

### `resutil add`

The `resutil add` command is used to add an experiment directory without executing any code.

You can use it as follows: `resutil add [comment] -d [DEPENDENCY1] [DEPENDENCY2]...`. This command adds an experiment directory named "comment" and sets its dependencies. The dependencies are other experiments that this experiment depends on.

For example, if you have two experiments `exp1` and `exp2` and a new experiment depends on them, you can add the new experiment with the following command: `resutil add "new experiment" -d exp1 exp2`. This will create a new experiment directory named "new experiment" and set `exp1` and `exp2` as its dependencies.

### `resutil list`

The `resutil list` command list experiments in the cloud storage.

### `resutil rm`

The `resutil rm` command removes experiments. You can use it as follows: resutil `resutil rm [-l] [-r] EXPERIMENT1 [EXPERIMENT2]...`.  `--local` or `-l` option removes only local experiment directory, whereas `--remote` or `-r` option for experiment data in cloud. Specifying neither options removes both experiments.

### `resutil comment` **EXPERIMENTAL**

`resutil comment [EXPERIMENT] [COMMENT]` add or modify a comment following timestamp in the experiment name. Both local and cloud experiment name will change if existing. It should be noted that Resutil regards a differnt experimental name as a different experiment, and this does not affect the name of the same experiment other users have already pull.

## Runtime Arguments

When running code that integrates Resutil, you can use the following two arguments:

`--resutil_comment COMMENT` Specifies a comment required at the start of execution. This prevents the need to prompt for a comment during execution.

`--resutil_no_interactive` Enables non-interactive mode. This prevents any user prompts during execution. This is useful when running as a batch job. If `--resutil_comment COMMENT` is not specified, no comment will be added to the experiment directory.

`--resutil_debug` Enables debug mode where a temporary directory is used as experiment directory. The temporary directory will not be unloaded to the cloud storage.

`--resutil_no_remote` Restrains from uploading results to the cloud storage

## Directory structure in the cloud storage

```plain text
BaseDir    # Base directory specified base_dir_id
├──MyProj  # Project directory
│   ├── aakuqj_20240511T174522_ex1.zip  # zip file of Experiment directory
│   │   ├── resutil-exp.yaml            # Experiment information
│   │   └── data.txt                    # Data (example)
│   ├── aamxrp_20240606T135747_ex2.zip
│   │   ├── resutil-exp.yaml
│   │   ├── data.txt
│   │   └── uncommited_files       # Uncommitted files
│   │       └── main.py
│   ...
│   
├──OtherProj
│
...
```

Experiment directories are formatted as `xxxxxx_yyyymmddTHHMMSS_comment`, where xxxxxx is timestamped for easy ordering and tab completion in shells.

## resutil-exp.yaml [WIP]

Each experiment directory has `resutil-exp.yaml`, which contains information to reproduce experimental results.

``` yaml
cmd: Execution command
params: Options at runtime
  hoo: xxx
  bar: 123
dependency: Dependencies (automatically extracted from directories in the command)
  - ex1
  - ex2
```

## how to publish

1. Change version number of `pyproject.toml`
1. Add v*.*.* tag will automatically deploy to PyPI
2. Add a [release note](https://github.com/KatayamaLab/resutil/releases) to GitHub such as:
    ```
    ## New Features
    - Add `--resutil_debug` and `--resutil_no_remote` options for trial-and-error phase
    - `-A` or `--all` options can be omitted for `resutil push/pull` commands

    ## Bug Fixed
    - Fix a bug resuitl does not works properly when git is not initialized
    ```