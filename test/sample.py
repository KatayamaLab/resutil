import resutil

from os import makedirs
from os.path import join
from time import sleep


@resutil.main()
def main_func(params):
    print("----Results can be stored in ", params.ex_dir)

    with open(join(params.ex_dir, "test.txt"), "w") as f:
        f.write("Hello World")

    subdir = join(params.ex_dir, "subdir")
    makedirs(subdir, exist_ok=True)
    with open(join(subdir, "subfile.txt"), "w") as f:
        f.write("Hello World!!!")

    for i in range(5):
        print(f"Sample program finish in {5-i} sec")
        sleep(1)


if __name__ == "__main__":
    main_func()
