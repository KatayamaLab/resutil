# Resutil
Japanese readme is [here](https://github.com/KatayamaLab/resutil/blob/main/README.ja.md)

## What is Resutil

**Resutil** is a utility to manage experimental result data obtained from Python projects. It also manages dependency such as codes and input data with result data. Data is synced to Google Cloud Storage (or Google Drive) for team sharing and collaboration.

## Why choose Resutil?

- **Simple**: Easy to install and can be quickly integrated into your project.  
- **High Reproducibility**: Tracks programs, input data, and experimental results.
- **Open-source and free**: Join development to future release of Resutil.


## Features

- Sync experimental data saved in a specific directory to Google Cloud Storage (default) or Google Drive after the program execution finished.
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

Prepare a Google Cloud service account key JSON for Cloud Storage (downloaded later in the setup steps) and save it as `key.json` in your project root. A typical key file looks like:

```json
{
    "type": "service_account",
    "project_id": "your-gcp-project",
    "private_key_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "private_key": "-----BEGIN PRIVATE KEY-----\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n-----END PRIVATE KEY-----\n",
    "client_email": "resutil-bot@your-gcp-project.iam.gserviceaccount.com",
    "client_id": "123456789012345678901",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
}
```

Initialize resutil

```bash
$ cd your-project-root-directory
$ resutil init
Input project name (resutil): MyProj
Input directory name to store results (results): results
Do you want to add .gitignore to results? (Y/n): Y
Input storage_type (gcs/gdrive): gcs
Input key file_path (key.json): key.json
Do you want to add key.json to .gitignore? (Y/n): Y
Input bucket name: resutil
✅ Initialized.
```

The bucket name is your Cloud Storage bucket, and `resutil-conf.yaml` will be created with this configuration.

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

Resutil supports Google Cloud Storage (default) and Google Drive. Below are the steps for each.

### Google Cloud Storage (recommended)

1. **Create a GCP project (if needed)**: In the [Google Cloud Console](https://console.cloud.google.com/), create or reuse a project.
2. **Enable Cloud Storage API**: Open [API Library](https://console.cloud.google.com/apis/library), search for “Cloud Storage”, and enable it.
3. **Create a bucket**: Go to [Cloud Storage Browser](https://console.cloud.google.com/storage/browser), click **Create Bucket**, and set a name (e.g., `resutil`) and location/class.
4. **Create a service account**: In [IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts), click **Create Service Account** and name it (e.g., `resutil-bot`).
5. **Grant permissions**: Give the service account the `Storage Object Admin` (or at least `Storage Object User` + `Storage Legacy Bucket Reader`) role for the bucket so it can read/write objects.
6. **Create and download a key**: On the service account page, open **Keys** → **Add Key** → **Create new key** → choose **JSON**, then download `key.json` and place it in your project root (add to `.gitignore`).
7. **Run `resutil init`**: Choose `gcs`, enter the path to `key.json`, and the bucket name you created.

### Google Drive

1. Create a folder in [Google Drive](https://drive.google.com/) and note the folder ID (the part after `folders/` in the URL).
2. In Google Cloud Console, create/reuse a project and a service account; download a JSON key.
3. Enable **Google Drive API** for the project.
4. Share the Drive folder with the service account email from the JSON key, giving `Editor` access.
5. Run `resutil init`, choose `gdrive`, set `key.json`, and provide the base folder ID.
    
## Commands

### `resutil init`

`resutil init` creates `resutil-conf.yaml` in your project folder such as:

```yaml
project_name: MyProj
results_dir: results/
storage_type: gcs
storage_config:
  backet_name: resutil  # bucket name
  key_file_path: key.json
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


## Environment Valuable

When running code that integrates Resutil, you can use the following environment valuables:

`RESUTIL_COMMENT` Specifies a comment required at the start of execution. This prevents the need to prompt for a comment during execution.

`RESUTIL_NO_INTERACTIVE` Enables non-interactive mode. This prevents any user prompts during execution. This is useful when running as a batch job. If `RESUTIL_COMMENT` is not specified, no comment will be added to the experiment directory.

`RESUTIIL_REMOTE` Restrains from uploading results to the cloud storage.

`RESUTIL_DEBUG` Enables debug mode where a temporary directory is used as experiment directory. The temporary directory will not be unloaded to the cloud storage.

## Saving checkpoint

For long-running executions, call `param.save_checkpoint()` to temporarily upload the data in the experiment directory.

## Directory structure in the cloud storage

```plain text
<bucket root>
├── MyProj  # Project directory
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
├── OtherProj
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
2. merge branch to `main`
3. Add v*.*.* tag will automatically deploy to PyPI
4. Add a [release note](https://github.com/KatayamaLab/resutil/releases) to GitHub such as:
    ```
    ## New Features
    - Add `--resutil_debug` and `--resutil_no_remote` options for trial-and-error phase
    - `-A` or `--all` options can be omitted for `resutil push/pull` commands

    ## Bug Fixed
    - Fix a bug resuitl does not works properly when git is not initialized
    ```
