import yaml


class ExpFile:
    def __init__(self, exp_file_path=None):
        if exp_file_path is None:
            return

        try:
            with open(exp_file_path, "r") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"experiment file {exp_file_path} does not exist.")

        self.dependency = conf["dependency"]
