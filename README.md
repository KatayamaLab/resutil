# Resutil

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

## Installation

Open terminal and run

```bash
$ pip install resutil
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

## Commands

### `resutil init`

`resutil init` creates `resutil-conf.yaml` in your project folder such as:

```yaml
project_name: MyProj
results_dir: results/
storage_type: box
storage_config:
  base_dir_id: xxxx
  key_file: key.json
```

### `resutil push`

The `resutil push` command is used to upload experimental data to the cloud that does not exist in the cloud result directory.

`resutil push [exp_name]` uploads experiment a specific directory to the cloud. Depending directorys included in `exp-config.yaml` are automtically uploaded. `--no-dependency` option restrain automatic dependency upload.

`resutil pull --all` will upload all experimental data to the cloud.

This is useful for keeping your local data up-to-date with the data stored in the cloud, especially when multiple people are working on the same project and updating the experimental data.

### `resutil pull`

The `resutil pull` command is used to download a specific experimental data from the cloud that does not exist in the local result directory.

`resutil pull [exp_name]` downloads experiment directory from cloud. Depending directorys included in `exp-config.yaml` are automtically downlowded. `--no-dependency` option restrain automatic dependency download.

`resutil pull --all` will download all experimental data from the cloud that is not currently in your local result directory.

This is useful for keeping your local data up-to-date with the data stored in the cloud, especially when multiple people are working on the same project and updating the experimental data.


### `resutil add`

The resutil add command is used to add an experiment directory without executing any code.

You can use it as follows: resutil `add [comment] -d [DEPENDENCY1] [DEPENDENCY2]...`. This command adds an experiment directory named "comment" and sets its dependencies. The dependencies are other experiments that this experiment depends on.

For example, if you have two experiments `exp1` and `exp2` and a new experiment depends on them, you can add the new experiment with the following command: `resutil add "new experiment" -d exp1 exp2`. This will create a new experiment directory named "new experiment" and set `exp1` and `exp2` as its dependencies.

## Directory structure in the cloud storage

```plain text
BaseDir    # Base directory specified base_dir_id
├──MyProj  # Project directory
│   ├── aakuqj_20240511T174522_ex1  # Experiment directory
│   │   ├── resutil-exp.yaml       # Experiment information
│   │   └── data.txt               # Data (example)
│   ├── aamxrp_20240606T135747_ex2
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


