import subprocess as sp
from xml.dom.minidom import parseString, Element
import numpy as np
from time import sleep

from typing import Dict


class GPUQuery(object):
    """Nvidia-SMI query generator and parser"""

    def __init__(self):
        self.text_buffer = ""
        self.xml_out = None

    @staticmethod
    def _nvsmi_call(as_xml=True):
        completed_process = sp.run(["nvidia-smi", "-q", "-x"], capture_output=True)
        return completed_process.stdout

    @staticmethod
    def parse_gpu_props(gpu: Element) -> Dict:
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

        process_nodelist = gpu.getElementsByTagName("process_info")
        processes = {}
        for node in process_nodelist:
            pid = int(node.childNodes[5].childNodes[0].data)
            pname = node.childNodes[9].childNodes[0].data.split("/")[-1]
            mem = int(node.childNodes[11].childNodes[0].data.split(" ")[0])
            completed_process = sp.run(
                ["ps", "--no-headers", "-p", "{}".format(pid), "-o", "user,comm,etime"],
                capture_output=True,
                text=True,
            )
            user, comm, lifetime = completed_process.stdout.split()
            processes[pid] = {}
            processes[pid]["name"] = pname
            processes[pid]["mem"] = mem
            processes[pid]["user"] = user
            processes[pid]["lifetime"] = lifetime
            processes[pid]["command"] = comm

        gpu_props["processes"] = processes

        return gpu_props

    def make_query(self):
        self.xml_out = parseString(GPUQuery._nvsmi_call())


class Tracker(object):
    """Object for polling and storing GPU stats"""

    def __init__(self, query, polling_rate=1, method="stdout", filename=None):
        self.query = query
        self.polling_rate = polling_rate
        self.props_buffer = None
        self.filename = None
        self.poll()
        self.num_gpus = len(self.props_buffer.keys())

    def poll(self):
        self.query.make_query()
        gpus = self.query.xml_out.getElementsByTagName("gpu")
        all_gpu_props = {i: GPUQuery.parse_gpu_props(gpu) for i, gpu in enumerate(gpus) }
        self.props_buffer = all_gpu_props
