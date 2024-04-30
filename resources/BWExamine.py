import json
import os
import sys

import h5py
import numpy as np
from h5py import Dataset, Group


def getChMap():
    newChs = np.zeros(4096, dtype=[("Row", "<i2"), ("Col", "<i2")])
    idx = 0
    ind = None
    for idx in range(4096):
        column = (idx // 64) + 1
        row = idx % 64 + 1
        if row == 0:
            row = 64
        if column == 0:
            column = 1

        newChs[idx] = (np.int16(row), np.int16(column))
        ind = np.lexsort((newChs["Col"], newChs["Row"]))
    if ind is None:
        sys.exit("Error: Channel map could not be created")
    return newChs[ind]


def get_recFile_properties(path, typ):
    h5 = h5py.File(path, "r")
    RAW = "EventsBasedSparseRaw"
    try:
        well_A1: Group = h5["Well_A1"]
        experiment_settings: Dataset = h5["ExperimentSettings"]
        well_A1_RAW: Dataset = h5[f"Well_A1/{RAW}"]
    except Exception as e:
        print(f"Error: {e}")
        return

    if RAW in well_A1.keys():
        experiment_settings_json: dict = json.loads(
            experiment_settings[0].decode("utf8")
        )
        parameters = {}
        parameters["Ver"] = "BW5"
        parameters["Typ"] = RAW
        parameters["nRecFrames"] = well_A1_RAW.shape[0] // 4096
        parameters["samplingRate"] = experiment_settings_json["TimeConverter"][
            "FrameRate"
        ]
        parameters["recordingLength"] = (
            parameters["nRecFrames"] / parameters["samplingRate"]
        )
        parameters["signalInversion"] = int(
            1
        )  # depending on the acq version it can be 1 or -1
        parameters["maxUVolt"] = int(4125)  # in uVolt
        parameters["minUVolt"] = int(-4125)  # in uVolt
        parameters["bitDepth"] = int(12)  # number of used bit of the 2 byte coding
        parameters["qLevel"] = (
            2 ^ parameters["bitDepth"]
        )  # quantized levels corresponds to 2^num of bit to encode the signal
        parameters["fromQLevelToUVolt"] = (
            parameters["maxUVolt"] - parameters["minUVolt"]
        ) / parameters["qLevel"]
        parameters["recElectrodeList"] = getChMap()[:]  # list of the recorded channels
        parameters["numRecElectrodes"] = len(parameters["recElectrodeList"])
    else:
        experiment_settings_json = json.loads(
            h5["ExperimentSettings"][0].decode("utf8")
        )
        parameters = {}
        parameters["Ver"] = "BW5"
        parameters["Typ"] = "WAV"
        parameters["nRecFrames"] = int(
            h5["Well_A1/WaveletBasedEncodedRaw"].shape[0]
            // 4096
            // experiment_settings_json["DataSettings"]["WaveletBasedRawCoefficients"][
                "FramesChunkSize"
            ]
            * experiment_settings_json["TimeConverter"]["FrameRate"]
        )
        parameters["samplingRate"] = experiment_settings_json["TimeConverter"][
            "FrameRate"
        ]
        parameters["recordingLength"] = (
            parameters["nRecFrames"] / parameters["samplingRate"]
        )
        parameters["signalInversion"] = int(
            1
        )  # depending on the acq version it can be 1 or -1
        parameters["maxUVolt"] = int(4125)  # in uVolt
        parameters["minUVolt"] = int(-4125)  # in uVolt
        parameters["bitDepth"] = int(12)  # number of used bit of the 2 byte coding
        parameters["qLevel"] = (
            2 ^ parameters["bitDepth"]
        )  # quantized levels corresponds to 2^num of bit to encode the signal
        parameters["fromQLevelToUVolt"] = (
            parameters["maxUVolt"] - parameters["minUVolt"]
        ) / parameters["qLevel"]
        parameters["recElectrodeList"] = getChMap()[:]  # list of the recorded channels
        parameters["numRecElectrodes"] = len(parameters["recElectrodeList"])
    return parameters


base_dir = os.path.expanduser("~/research/resources/")
os.chdir(base_dir)
path = r"BW5 Test File.brw"  # Export ch helper file example

fileInfo = {}
h5 = h5py.File(path, "r")
# ChsList = h5["/3BRecInfo/3BMeaStreams/Raw/Chs"][:]
es_settings_list = h5["ExperimentSettings"][:]
for setting in es_settings_list:
    print(setting)

get_recFile_properties(path, 1)
