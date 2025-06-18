import docker
import os

client = docker.from_env()

def run_container(image="sandbox", name="py-sandbox"):
    pwd = os.getcwd()

    mounts = [
        docker.types.Mount(target="/mnt/data",
                           source=f"{pwd}/data",
                           type="bind",
                           read_only=False),
        docker.types.Mount(target="/mnt/jupyter_sessions",
                           source=f"{pwd}/jupyter_sessions",
                           type="bind",
                           read_only=False),
        docker.types.Mount(target="/home/sandbox/.local",
                           source=f"{pwd}/python_env",
                           type="bind",
                           read_only=False),
    ]

    container = client.containers.run(
        image=image,
        name=name,
        detach=True,
        ports={"5002/tcp": 5002, "4040/tcp": 4040, "4041/tcp": 4041},
        user="1000:1000",
        read_only=True,
        cap_drop=["ALL"],
        security_opt=[f"seccomp={pwd}/seccomp-prof.json"],
        tmpfs={"/tmp": "rw,exec,size=512m"},
        mounts=mounts,
    )
    print("Started container:", container.short_id)

if __name__ == "__main__":
    run_container()
