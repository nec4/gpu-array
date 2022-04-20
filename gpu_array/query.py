import subprocess
from xml.dom.minidom import parseString, Element
from typing import Dict


class GPUQuery(object):
    """Nvidia-SMI XML query generator and parser"""

    def __init__(self):
        self.xml_out = None

    @staticmethod
    def _nvsmi_call() -> subprocess.CompletedProcess:
        """Subprocess call to nvidia-smi specifying XML output
        of GPU information.

        Returns
        -------
        completed_process:
            CompletedProcess instance containing the XML output of nvidia-smi
        """
        completed_process = subprocess.run(
            ["nvidia-smi", "-q", "-x"], capture_output=True
        )
        return completed_process

    @staticmethod
    def parse_gpu_props(gpu: Element) -> Dict:
        """Method for parsing nvidia-smi XML output

        Parameters
        ----------
        gpu:
            An XML minidom Element instance that represents
            a "GPU" node in the xml minidom tree

        Returns
        -------
        gpu_props:
            dictionary of the gpu properties
        """
        gpu_props = {}

        gpu_props["name"] = (
            gpu.getElementsByTagName("product_name")[0].childNodes[0].data
        )
        gpu_props["total_mem"] = int(
            gpu.getElementsByTagName("fb_memory_usage")[0]
            .childNodes[1]
            .childNodes[0]
            .data.split(" ")[0]
        )
        gpu_props["used_mem"] = int(
            gpu.getElementsByTagName("fb_memory_usage")[0]
            .childNodes[3]
            .childNodes[0]
            .data.split(" ")[0]
        )

        gpu_props["fan"] = int(
            gpu.getElementsByTagName("fan_speed")[0].childNodes[0].data.split(" ")[0]
        )

        gpu_props["temp"] = float(
            gpu.getElementsByTagName("temperature")[0]
            .childNodes[1]
            .childNodes[0]
            .data.split(" ")[0]
        )
        gpu_props["max_temp"] = float(
            gpu.getElementsByTagName("temperature")[0]
            .childNodes[3]
            .childNodes[0]
            .data.split(" ")[0]
        )

        gpu_props["used_power"] = float(
            gpu.getElementsByTagName("power_readings")[0]
            .childNodes[5]
            .childNodes[0]
            .data.split(" ")[0]
        )
        gpu_props["power_limit"] = float(
            gpu.getElementsByTagName("power_readings")[0]
            .childNodes[7]
            .childNodes[0]
            .data.split(" ")[0]
        )

        gpu_props["utilization"] = int(
            gpu.getElementsByTagName("utilization")[0]
            .childNodes[1]
            .childNodes[0]
            .data.split(" ")[0]
        )

        process_nodelist = gpu.getElementsByTagName("process_info")
        processes = {}
        for node in process_nodelist:
            pid = int(node.childNodes[5].childNodes[0].data)
            pname = node.childNodes[9].childNodes[0].data.split("/")[-1]
            mem = int(node.childNodes[11].childNodes[0].data.split(" ")[0])
            completed_process = subprocess.run(
                ["ps", "--no-headers", "-p", "{}".format(pid), "-o", "user,comm,etime"],
                capture_output=True,
                text=True,
            )

            # Handle improper/incomplete output
            if len(completed_process.stdout.split()) == 3:
                user, comm, lifetime = completed_process.stdout.split()
            else:
                continue
            processes[pid] = {}
            processes[pid]["name"] = pname
            processes[pid]["mem"] = mem
            processes[pid]["user"] = user
            processes[pid]["lifetime"] = lifetime
            processes[pid]["command"] = comm

        gpu_props["processes"] = processes

        return gpu_props

    def make_query(self):
        """Method parsing and storing minidom-parsed XML
        from nvidia-smi"""
        self.xml_out = parseString(GPUQuery._nvsmi_call().stdout)


class Tracker(object):
    """Object for polling and storing GPU stats

    Parameters
    ----------
    query:
        GPUquery instance
    polling_rate:
        The rate at which queries about GPU information should be made
    """

    def __init__(self, query: GPUQuery, polling_rate: int = 1):
        self.query = query
        self.polling_rate = polling_rate
        self.props_buffer = None
        self.filename = None
        self.poll()
        self.num_gpus = len(self.props_buffer.keys())

    def poll(self):
        """Method that makes a query, parses the xml, and stores the
        parsed dictionary in a volatile buffer attribute, Tracker.props_buffer.
        Each call to poll() overwrites this buffer with the newest parsed output.
        """
        self.query.make_query()
        gpus = self.query.xml_out.getElementsByTagName("gpu")
        all_gpu_props = {i: GPUQuery.parse_gpu_props(gpu) for i, gpu in enumerate(gpus)}
        self.props_buffer = all_gpu_props
