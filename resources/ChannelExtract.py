import sys

# assert (sys.version_info[0], sys.version_info[1]) == (
#     3,
#     7,
# ), "Please install/setup Python environment: Version-3.7"
import numpy as np
import h5py
import json
import os
import time
import scipy
import scipy.signal
import pandas as pd
import datetime
from tqdm import tqdm
from pythonnet import clr_loader
import matplotlib.pyplot as plt
import struct
from h5py import Dataset, Group
import ctypes

# For the code to run, BrianWave5 software needs to be installed, the path for the *.dll files should be changed below accordingly
_3Brain = ctypes.CDLL("/Users/booka66/research/resources/3Brain.BrainWave.IO.dll")
BrwFile = _3Brain.BrwFile
# clr.AddReference(
#     os.path.join("/Users/booka66/research/resources/", "3Brain.BrainWave.IO.dll")
# )
# from _3Brain.BrainWave.IO import BrwFile


def string2TupList(strInput):
    strInput = str(strInput)
    tupleStrings = strInput.split("),")
    tupList = []
    for tup_str in tupleStrings:
        values = tup_str.split(",")
        values[0] = values[0].replace("(", "")
        values[1] = values[1].replace(")", "")
        for k in values:
            tupVals = (int(values[0]), int(values[1]))
            tupList.append(tupVals)
    tupListFin = tupList[::2]
    return tupListFin


def getChMap():
    newChs = np.zeros(4096, dtype=[("Row", "<i2"), ("Col", "<i2")])
    idx = 0
    for idx in range(4096):
        column = (idx // 64) + 1
        row = idx % 64 + 1
        if row == 0:
            row = 64
        if column == 0:
            column = 1

        newChs[idx] = (np.int16(row), np.int16(column))
        ind = np.lexsort((newChs["Col"], newChs["Row"]))
    return newChs[ind]


def get_BW5_recording_file_props(path, typ):
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


####To do:
# Check graphing: when no downsampling case
# Only graphs one and we don't have the skip issue


###User input
##############
# file path input
fpath = "/Users/booka66/research/resources/BW5_Test_File.brw"

# Check the original sampling rate and recording length
h5 = h5py.File(fpath, "r")
parameters = get_BW5_recording_file_props(fpath, 1)
OGsamplingRate = parameters["samplingRate"]
recLength = parameters["recordingLength"]
h5.close()

# Select channels
# chInput = input(
#     "Enter the channels you want to record as comma separated pairs in parentheses as (row, column), e.g. '(2,4), (13,40), ...'\n"
# )

chInt = string2TupList("(1, 1), (1, 2)")

# chInt = string2TupList(chInput)

##Channel verification
channelVerify = "(1, 1), (1, 2)"
channelVerifyTup = string2TupList(channelVerify)
if channelVerifyTup == chInt:
    print("Channels match.  Proceed with program")
else:
    print(
        "Channels do not match.  Please end the program, verify channel indices for export, and start over."
    )

# Downsampling option
downsampleQ = input(
    "Enter in the downsampling frequency.  (If you do not want to downsample, enter 'n'):    "
)
if downsampleQ == "n":
    downsampleFreq = int(OGsamplingRate)
else:
    downsampleFreq = int(downsampleQ)

# Input metadata from recorder
recorderName = "Jake Cahoon"
paradigm = "IDK"
brainRegion = "Hippocampus"
print("")
##############

# Initialize and prepare the channels list
if chInt.count((1, 1)) != 0:
    chInt.insert(0, (64, 64))
elif chInt.count((64, 64)) != 0:
    chInt.insert(0, (1, 64))
elif chInt.count((1, 64)) != 0:
    chInt.insert(0, (64, 1))
else:
    chInt.insert(0, (1, 1))
ChInt = np.array(chInt, dtype=[("Row", "<i2"), ("Col", "<i2")])


##Definitions of helper functions used in the program


class writeBrw:
    def __init__(self, inputFilePath, outputFile, parameters):
        self.path = inputFilePath
        self.fileName = outputFile
        self.description = parameters["Ver"]
        self.version = parameters["Typ"]
        self.samplingrate = parameters["samplingRate"]
        self.frames = parameters["nRecFrames"]
        self.signalInversion = parameters["signalInversion"]
        self.maxVolt = parameters["maxUVolt"]
        self.minVolt = parameters["minUVolt"]
        self.bitdepth = parameters["bitDepth"]
        self.chs = parameters["recElectrodeList"]
        self.QLevel = np.power(2, parameters["bitDepth"])
        self.fromQLevelToUVolt = (self.maxVolt - self.minVolt) / self.QLevel

    def createNewBrw(self):
        newName = self.fileName
        new = h5py.File(newName, "w")

        new.attrs.__setitem__("Description", self.description)
        new.attrs.__setitem__("Version", self.version)
        new.create_dataset("/3BRecInfo/3BRecVars/SamplingRate", data=[np.float64(100)])
        # new.create_dataset('/3BRecInfo/3BRecVars/NewSampling', data=[np.float64(self.samplingrate)])
        new.create_dataset(
            "/3BRecInfo/3BRecVars/NRecFrames", data=[np.float64(self.frames)]
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/SignalInversion",
            data=[np.int32(self.signalInversion)],
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/MaxVolt", data=[np.int32(self.maxVolt)]
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/MinVolt", data=[np.int32(self.minVolt)]
        )
        new.create_dataset(
            "/3BRecInfo/3BRecVars/BitDepth", data=[np.int32(self.bitdepth)]
        )
        new.create_dataset("/3BRecInfo/3BMeaStreams/Raw/Chs", data=[self.chs])

        try:
            del new["/3BRecInfo/3BMeaStreams/Raw/Chs"]
        except:
            del new["/3BRecInfo/3BMeaStreams/WaveletCoefficients/Chs"]

        del new["/3BRecInfo/3BRecVars/NRecFrames"]
        del new["/3BRecInfo/3BRecVars/SamplingRate"]

        self.newDataset = new
        # self.brw.close()

    def writeRaw(self, rawToWrite, typeFlatten="F"):
        if rawToWrite.ndim == 1:
            newRaw = rawToWrite
        else:
            newRaw = np.int16(rawToWrite.flatten(typeFlatten))

        if "/3BData/Raw" in self.newDataset:
            dset = self.newDataset["3BData/Raw"]
            dset.resize((dset.shape[0] + newRaw.shape[0],))
            dset[-newRaw.shape[0] :] = newRaw

        else:
            self.newDataset.create_dataset("/3BData/Raw", data=newRaw, maxshape=(None,))

    def writeChs(self, chs):
        self.newDataset.create_dataset("/3BRecInfo/3BMeaStreams/Raw/Chs", data=chs)

    def witeFrames(self, frames):
        self.newDataset.create_dataset(
            "/3BRecInfo/3BRecVars/NRecFrames", data=[np.int64(frames)]
        )

    def writeSamplingFreq(self, fs):
        self.newDataset.create_dataset(
            "/3BRecInfo/3BRecVars/SamplingRate", data=[np.float64(fs)]
        )

    def appendBrw(self, fName, frames, rawToAppend, typeFlatten="F"):
        brwAppend = h5py.File(fName, "a")

        signalInversion = brwAppend["3BRecInfo/3BRecVars/SignalInversion"]
        maxVolt = brwAppend["3BRecInfo/3BRecVars/MaxVolt"][0]
        minVolt = brwAppend["3BRecInfo/3BRecVars/MinVolt"][0]
        QLevel = np.power(2, brwAppend["3BRecInfo/3BRecVars/BitDepth"][0])
        fromQLevelToUVolt = (maxVolt - minVolt) / QLevel

        newFrame = frames
        del brwAppend["/3BRecInfo/3BRecVars/NRecFrames"]
        brwAppend.create_dataset(
            "/3BRecInfo/3BRecVars/NRecFrames", data=[np.int64(newFrame)]
        )

        if rawToAppend.ndim != 1:
            rawToAppend = np.int16(rawToAppend.flatten(typeFlatten))

        dset = brwAppend["3BData/Raw"]
        dset.resize((dset.shape[0] + rawToAppend.shape[0],))
        dset[-rawToAppend.shape[0] :] = rawToAppend

        brwAppend.close()

    def close(self):
        self.newDataset.close()


def parameter(h5):
    parameters = {}
    parameters["nRecFrames"] = h5["/3BRecInfo/3BRecVars/NRecFrames"][0]
    parameters["samplingRate"] = h5["/3BRecInfo/3BRecVars/SamplingRate"][0]
    parameters["recordingLength"] = (
        parameters["nRecFrames"] / parameters["samplingRate"]
    )
    parameters["signalInversion"] = h5["/3BRecInfo/3BRecVars/SignalInversion"][
        0
    ]  # depending on the acq version it can be 1 or -1
    parameters["maxUVolt"] = h5["/3BRecInfo/3BRecVars/MaxVolt"][0]  # in uVolt
    parameters["minUVolt"] = h5["/3BRecInfo/3BRecVars/MinVolt"][0]  # in uVolt
    parameters["bitDepth"] = h5["/3BRecInfo/3BRecVars/BitDepth"][
        0
    ]  # number of used bit of the 2 byte coding
    parameters["qLevel"] = (
        2 ^ parameters["bitDepth"]
    )  # quantized levels corresponds to 2^num of bit to encode the signal
    parameters["fromQLevelToUVolt"] = (
        parameters["maxUVolt"] - parameters["minUVolt"]
    ) / parameters["qLevel"]
    parameters["recElectrodeList"] = (
        ChInt  # list(h5['/3BRecInfo/3BMeaStreams/Raw/Chs'])  # list of the recorded channels
    )
    parameters["numRecElectrodes"] = len(parameters["recElectrodeList"])
    return parameters


def Digital_to_Analog(parameters):
    ADCCountsToMV = parameters["signalInversion"] * parameters["fromQLevelToUVolt"]
    MVOffset = parameters["signalInversion"] * parameters["minUVolt"]
    return ADCCountsToMV, MVOffset


def downsample_channel(data, freq_ratio):
    re_sampleRatio = int(data.shape[0] / freq_ratio)
    data_downsampled = scipy.signal.resample(data, re_sampleRatio)
    return data_downsampled


def get_chfile_properties(path):
    fileInfo = {}
    h5 = h5py.File(path, "r")
    fileInfo["recFrames"] = h5["/3BRecInfo/3BRecVars/NRecFrames"][0]
    fileInfo["recSampling"] = h5["/3BRecInfo/3BRecVars/SamplingRate"][0]
    fileInfo["newSampling"] = (
        downsampleFreq  ######## This is the test sampling freq that we want to get
    )
    # fileInfo['newSampling'] = 1024
    fileInfo["recLength"] = fileInfo["recFrames"] / fileInfo["recSampling"]
    fileInfo["recElectrodeList"] = (
        ChInt  # h5['/3BRecInfo/3BMeaStreams/Raw/Chs'][:]  # list of the recorded channels ######This also doesn't exist changed to getChMap
    )
    fileInfo["numRecElectrodes"] = len(fileInfo["recElectrodeList"])
    fileInfo["Ver"] = (
        1  # h5['/3BRecInfo/3BRecVars/Ver'][0] ##This doesn't exist either; I'm just going to put 1 as the value
    )
    fileInfo["Typ"] = (
        1  # h5['/3BRecInfo/3BRecVars/Typ'][0] ##I'm just going to put 1 as the value
    )
    fileInfo["start"] = (
        0  # h5['/3BRecInfo/3BRecVars/startTime'][0] ##I'm going to put 0
    )
    fileInfo["end"] = recLength  # h5['/3BRecInfo/3BRecVars/endTime'][0]  #
    h5.close()
    return fileInfo


def get_recFile_properties(path, typ):
    h5 = h5py.File(path, "r")

    parameters = {}
    parameters["Ver"] = "BW4"
    parameters["nRecFrames"] = h5["/3BRecInfo/3BRecVars/NRecFrames"][0]
    parameters["samplingRate"] = h5["/3BRecInfo/3BRecVars/SamplingRate"][0]
    parameters["recordingLength"] = (
        parameters["nRecFrames"] / parameters["samplingRate"]
    )
    parameters["signalInversion"] = h5["/3BRecInfo/3BRecVars/SignalInversion"][
        0
    ]  # depending on the acq version it can be 1 or -1
    parameters["maxUVolt"] = h5["/3BRecInfo/3BRecVars/MaxVolt"][0]  # in uVolt
    parameters["minUVolt"] = h5["/3BRecInfo/3BRecVars/MinVolt"][0]  # in uVolt
    parameters["bitDepth"] = h5["/3BRecInfo/3BRecVars/BitDepth"][
        0
    ]  # number of used bit of the 2 byte coding
    parameters["qLevel"] = (
        2 ^ parameters["bitDepth"]
    )  # quantized levels corresponds to 2^num of bit to encode the signal
    parameters["fromQLevelToUVolt"] = (
        parameters["maxUVolt"] - parameters["minUVolt"]
    ) / parameters["qLevel"]
    try:
        parameters["recElectrodeList"] = (
            ChInt  # h5['/3BRecInfo/3BMeaStreams/Raw/Chs'][:]  # list of the recorded channels
        )
        parameters["Typ"] = "RAW"
    except:
        parameters["recElectrodeList"] = h5[
            "/3BRecInfo/3BMeaStreams/WaveletCoefficients/Chs"
        ][:]
        parameters["Typ"] = "WAV"
    parameters["numRecElectrodes"] = len(parameters["recElectrodeList"])

    # For BW5:
    if "Raw" in h5["Well_A1"].keys():
        json_s = json.loads(h5["ExperimentSettings"][0].decode("utf8"))
        parameters = {}
        parameters["Ver"] = "BW5"
        parameters["Typ"] = "RAW"
        parameters["nRecFrames"] = h5["Well_A1/Raw"].shape[0] // 4096
        parameters["samplingRate"] = json_s["TimeConverter"]["FrameRate"]
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
        json_s = json.loads(h5["ExperimentSettings"][0].decode("utf8"))
        parameters = {}
        parameters["Ver"] = "BW5"
        parameters["Typ"] = "WAV"
        parameters["nRecFrames"] = int(
            h5["Well_A1/WaveletBasedEncodedRaw"].shape[0]
            // 4096
            // json_s["DataSettings"]["WaveletBasedRawCoefficients"]["FramesChunkSize"]
            * json_s["TimeConverter"]["FrameRate"]
        )
        parameters["samplingRate"] = json_s["TimeConverter"]["FrameRate"]
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


# def extBW4_WAV(chfileName, recfileName, chfileInfo, parameters):
#     parameters["recElectrodeList"] = getChMap()
#     b = time.time()
#     chs, ind_rec, ind_ch = np.intersect1d(
#         parameters["recElectrodeList"],
#         chfileInfo["recElectrodeList"],
#         return_indices=True,
#     )
#
#     newSampling = int(chfileInfo["newSampling"])
#     output_file_name = recfileName.split(".")[0] + "_resample_" + str(newSampling)
#     output_path = output_file_name + ".brw"
#     parameters["freq_ratio"] = parameters["samplingRate"] / chfileInfo["newSampling"]
#     fs = chfileInfo["newSampling"]  # desired sampling frequency
#     block_size = 250000
#
#     print("Downsampling File # ", output_path)
#     dset = writeBrw(recfileName, output_path, parameters)
#     dset.createNewBrw()
#
#     newChs = np.zeros(len(chs), dtype=[("Row", "<i2"), ("Col", "<i2")])
#     idx = 0
#     for ch in chs:
#         newChs[idx] = (np.int16(ch[0]), np.int16(ch[1]))
#         idx += 1
#
#     ind = np.lexsort((newChs["Col"], newChs["Row"]))
#     newChs = newChs[ind]
#     start = 0
#     idx_a = ind_rec.copy()
#     data = BrwFile.Open(recfileName)
#     consumer = object()
#     info = data.get_MeaExperimentInfo()
#     frameRate = float(info.get_SamplingRate())
#     dur = int(info.get_TimeDuration().get_TotalSeconds())
#     startFrame = np.floor(start * info.get_SamplingRate())
#     endFrame = startFrame + np.floor(dur * info.get_SamplingRate())
#     numReading = int(np.floor(dur * info.get_SamplingRate() / block_size))
#
#     s = time.time()
#     nrecFrame = 0
#     for cnk in tqdm(range(numReading), desc="Export & downsampling Progress"):
#         raw = np.zeros((block_size, len(ind_rec)))
#
#         tmp = data.ReadRawData(
#             int(startFrame + cnk * block_size),
#             block_size,
#             data.get_SourceChannels(),
#             consumer,
#         )
#         # tmp is a 3D array, first index is the well number (in case of mutliwells, for single chip there will be only one well),
#         # the second index is the channel, the third index the time frame
#         count = 0
#         for i in tqdm(ind_rec, desc="Extracting individual channel"):
#             ext = np.fromiter(
#                 tmp[0][int(i)], int
#             )  # here values are converted in voltage
#             raw[:, count] = ext[:]
#             count += 1
#
#         raw_resample = downsample_channel(raw, parameters["freq_ratio"])
#         raw_resample = np.transpose(raw_resample)
#
#         nrecFrame += raw_resample.shape[1]
#
#         if cnk <= 0:
#             dset.writeRaw(raw_resample[ind, :], typeFlatten="F")
#             dset.writeSamplingFreq(fs)
#             dset.witeFrames(nrecFrame)
#             dset.writeChs(newChs)
#             dset.close()
#         else:
#             dset.appendBrw(output_path, nrecFrame, raw_resample[ind, :])
#     data.Close()
#     return time.time() - s, output_path
#
#
# def extBW4_RAW(chfileName, recfileName, chfileInfo, parameters):
#     chs, ind_rec, ind_ch = np.intersect1d(
#         parameters["recElectrodeList"],
#         chfileInfo["recElectrodeList"],
#         return_indices=True,
#     )
#     newSampling = int(chfileInfo["newSampling"])
#     output_file_name = recfileName.split(".")[0] + "_resample_" + str(newSampling)
#     output_path = output_file_name + ".brw"
#     parameters["freq_ratio"] = parameters["samplingRate"] / chfileInfo["newSampling"]
#     fs = chfileInfo["newSampling"]  # desired sampling frequency
#     block_size = 100000
#
#     chunks = np.arange(block_size, parameters["nRecFrames"], block_size)
#     print("Downsampling File #", output_path)
#     dset = writeBrw(recfileName, output_path, parameters)
#     dset.createNewBrw()
#
#     newChs = np.zeros(len(chs), dtype=[("Row", "<i2"), ("Col", "<i2")])
#     idx = 0
#     for ch in chs:
#         newChs[idx] = (np.int16(ch[0]), np.int16(ch[1]))
#         idx += 1
#
#     ind = np.lexsort((newChs["Col"], newChs["Row"]))
#     newChs = newChs[ind]
#
#     start = 0
#     h5 = h5py.File(recfileName, "r")
#     idx_a = ind_rec.copy()
#     idd = []
#     for i in range(block_size):
#         idd.extend(idx_a)
#         idx_a = idx_a + parameters["numRecElectrodes"]
#
#     s = time.time()
#     nrecFrame = 0
#     for cnk in tqdm(chunks, desc="Downsampling & Export Progress"):
#         end = cnk * parameters["numRecElectrodes"]
#         data = np.array(h5["/3BData/Raw"][start:end])
#         data = data[idd]
#         data = data.reshape(block_size, len(chs))
#
#         data_resample = downsample_channel(data, parameters["freq_ratio"])
#         resamp_frame = data_resample.shape[0]
#
#         nrecFrame += resamp_frame
#         res = np.zeros((len(chs), resamp_frame))
#
#         ch = 0
#         for channel in range(res.shape[0]):
#             res[channel, :] = data_resample[:, ch]
#             ch += 1
#
#         if cnk <= block_size:
#             dset.writeRaw(res[ind, :], typeFlatten="F")
#             dset.writeSamplingFreq(fs)
#             dset.witeFrames(nrecFrame)
#             dset.writeChs(newChs)
#             dset.close()
#         else:
#             dset.appendBrw(output_path, nrecFrame, res[ind, :])
#
#         start = end
#     h5.close()
#     totTime = time.time() - s
#
#     return totTime, output_path


def extBW5_WAV(chfileName, recfileName, chfileInfo, parameters):
    b = time.time()
    chs, ind_rec, ind_ch = np.intersect1d(
        parameters["recElectrodeList"],
        chfileInfo["recElectrodeList"],
        return_indices=True,
    )
    exit()
    ############
    newSampling = int(chfileInfo["newSampling"])
    output_file_name = recfileName.split(".")[0] + "_resample_" + str(newSampling)
    output_path = output_file_name + ".brw"
    parameters["freq_ratio"] = parameters["samplingRate"] / chfileInfo["newSampling"]
    fs = chfileInfo["newSampling"]  # desired sampling frequency
    block_size = 250000

    print("Downsampling File # ", output_path)
    dset = writeBrw(recfileName, output_path, parameters)
    dset.createNewBrw()

    newChs = np.zeros(len(chs), dtype=[("Row", "<i2"), ("Col", "<i2")])
    idx = 0
    for ch in chs:
        newChs[idx] = (np.int16(ch[0]), np.int16(ch[1]))
        idx += 1

    ind = np.lexsort((newChs["Col"], newChs["Row"]))
    newChs = newChs[ind]
    start = 0
    idx_a = ind_rec.copy()
    consumer = object()
    data = BrwFile.Open(recfileName)
    info = data.get_MeaExperimentInfo()
    frameRate = float(info.get_SamplingRate())
    # dur = int(info.get_RecordingDuration().get_TotalSeconds())
    dur = int(info.get_TimeDuration().get_TotalSeconds())
    startFrame = np.floor(start * info.get_SamplingRate())
    endFrame = startFrame + np.floor(dur * info.get_SamplingRate())
    numReading = int(np.floor(dur * info.get_SamplingRate() / block_size))
    if numReading <= 0:
        numReading = int(np.floor(dur * info.get_SamplingRate() / (block_size / 10)))
        block_size = int(block_size / 10)
    # print(startFrame,endFrame,block_size)
    #    print(numReading,dur,info.get_RecordingDuration().get_TotalSeconds(),dur * info.get_SamplingRate() / block_size)

    s = time.time()
    nrecFrame = 0
    for cnk in tqdm(range(numReading), desc="Export & downsampling Progress"):
        raw = np.zeros((block_size, len(ind_rec)))

        tmp = data.ReadRawData(
            int(startFrame + cnk * block_size),
            block_size,
            data.get_SourceChannels(),
            consumer,
        )
        # tmp is a 3D array, first index is the well number (in case of mutliwells, for single chip there will be only one well),
        # the second index is the channel, the third index the time frame
        count = 0
        for i in tqdm(ind_rec, desc="Extracting individual channel"):
            ext = np.fromiter(
                tmp[0][int(i)], int
            )  # here values are converted in voltage
            raw[:, count] = ext[:]
            count += 1

        raw_resample = downsample_channel(raw, parameters["freq_ratio"])
        raw_resample = np.transpose(raw_resample)

        nrecFrame += raw_resample.shape[1]

        if cnk <= 0:
            dset.writeRaw(raw_resample[ind, :], typeFlatten="F")
            dset.writeSamplingFreq(fs)
            dset.witeFrames(nrecFrame)
            dset.writeChs(newChs)
            dset.close()
        else:
            dset.appendBrw(output_path, nrecFrame, raw_resample[ind, :])
    data.Close()
    return time.time() - s, output_path


def extBW5_RAW(recfileName, parameters):
    # chs, ind_rec, ind_ch = np.intersect1d(
    #     parameters["recElectrodeList"],
    #     parameters["recElectrodeList"],
    #     return_indices=True,
    # )
    chs = parameters["recElectrodeList"]
    ind_rec = ind_ch = list(range(len(chs)))
    output_file_name = recfileName.split(".")[0] + "_resample_" + str(downsampleFreq)
    output_path = output_file_name + ".brw"
    parameters["freq_ratio"] = parameters["samplingRate"] / downsampleFreq
    block_size = 100000

    chunks = np.arange(block_size, parameters["nRecFrames"], block_size)
    print("Downsampling File #", output_path)
    dset = writeBrw(recfileName, output_path, parameters)
    dset.createNewBrw()

    newChs = np.zeros(len(chs), dtype=[("Row", "<i2"), ("Col", "<i2")])
    idx = 0
    for ch in chs:
        newChs[idx] = (np.int16(ch[0]), np.int16(ch[1]))
        idx += 1

    ind = np.lexsort((newChs["Col"], newChs["Row"]))
    newChs = newChs[ind]

    start = 0
    h5 = h5py.File(recfileName, "r")
    idx_a = ind_rec.copy()
    idd = []
    for i in range(block_size):
        idd.extend(idx_a)
        idx_a.append(parameters["numRecElectrodes"])

    s = time.time()
    nrecFrame = 0

    for cnk in tqdm(chunks, desc="Downsampling & Export Progress"):
        print("This is the chunk: ", cnk)
        end = int(cnk * float(parameters["numRecElectrodes"]))
        data = np.array(h5["Well_A1/Raw"][start:end])
        data = data[idd]
        data = data.reshape(block_size, len(chs))

        data_resample = downsample_channel(data, parameters["freq_ratio"])
        resamp_frame = data_resample.shape[0]

        nrecFrame += resamp_frame
        res = np.zeros((len(chs), resamp_frame))

        ch = 0
        for channel in range(res.shape[0]):
            res[channel, :] = data_resample[:, ch]
            ch += 1

        if cnk <= block_size:
            dset.writeRaw(res[ind, :], typeFlatten="F")
            dset.writeSamplingFreq(downsampleFreq)
            dset.witeFrames(nrecFrame)
            dset.writeChs(newChs)
            dset.close()
        else:
            dset.appendBrw(output_path, nrecFrame, res[ind, :])

        start = end
    h5.close()
    totTime = time.time() - s
    return totTime, output_path


def file_check(path, filename):
    chfileName = path + "\\" + filename
    chfilePath = os.path.join(path, filename)
    chfileInfo = get_chfile_properties(chfilePath)
    recfileName = "_".join(filename.split("_")[0:-1]) + ".brw"
    recfilePath = os.path.join(path, recfileName)
    parameters = get_recFile_properties(
        recfilePath, 1
    )  # I just put a 1 here and it works
    if (
        parameters["nRecFrames"] == chfileInfo["recFrames"]
        and parameters["samplingRate"] == chfileInfo["recSampling"]
    ):
        filematch = True
    else:
        # filematch =  False
        print("filematch failed")

    return (chfilePath, recfilePath, chfileInfo, parameters, filematch)


def main(fpath):
    # Set usage variables
    fileCount = 1

    # get ch file properties
    h5 = h5py.File(fpath, "r")
    parameters = get_BW5_recording_file_props(
        fpath, 1
    )  # This didn't work since I didn't know chfileInfo['Ver'] it had a .lower on it but removed this since is an int but I just set it at 1 and it works
    h5.close()

    totTime, output_path = extBW5_RAW(fpath, parameters)
    print(
        "\n #",
        fileCount,
        " Down Sampled Output File Location: ",
        output_path,
        "\n Time to Downsample: ",
        totTime,
    )

    fileCount += 1

    # Prepare for export
    with h5py.File(output_path, "r") as file:
        data = file["/3BRecInfo/3BMeaStreams/Raw/Chs"][:]
        data1 = np.array(data, dtype=float)

        # Store relevant Values
        expFileInfo = {}
        expFileInfo["ChsList"] = file["/3BRecInfo/3BMeaStreams/Raw/Chs"][:]
        expFileInfo["recFrames"] = file["/3BRecInfo/3BRecVars/NRecFrames"][0]
        expFileInfo["recSampling"] = file["/3BRecInfo/3BRecVars/SamplingRate"][0]
        expFileInfo["Chs"] = file["/3BRecInfo/3BMeaStreams/Raw/Chs"][:]
        expFileInfo["RawData"] = file["/3BData/Raw"][:]

        ###ADC count to mV conversion
        print("\nOriginal sampling rate: ", OGsamplingRate)
        print("Downsampling rate: ", downsampleFreq)
        print("Export channels list: ", expFileInfo["Chs"][1 : len(expFileInfo["Chs"])])
        signalInversion = file["/3BRecInfo/3BRecVars/SignalInversion"][
            0
        ]  # depending on the acq version it can be 1 or -1
        maxUVolt = file["/3BRecInfo/3BRecVars/MaxVolt"][0]  # in uVolt
        minUVolt = file["/3BRecInfo/3BRecVars/MinVolt"][0]  # in uVolt
        bitDepth = file["/3BRecInfo/3BRecVars/BitDepth"][
            0
        ]  # number of used bit of the 2 byte coding
        qLevel = (
            2 ^ bitDepth
        )  # quantized levels corresponds to 2^num of bit to encode the signal
        fromQLevelToUVolt = (maxUVolt - minUVolt) / qLevel
        ADCCountsToMV = signalInversion * fromQLevelToUVolt
        MVOffset = signalInversion * minUVolt
        file.close()
    # convRawData = [(en * ADCCountsToMV) + MVOffset for en in data1]
    convRawData = [
        (en / (2 ^ bitDepth - 1) * (maxUVolt - minUVolt) + minUVolt) / (10**6) * 2.2 - 8
        for en in data1
    ]

    # Set time vector for graphing
    singleChLen = int(len(data) / len(expFileInfo["Chs"]))
    x = np.arange(0, singleChLen / downsampleFreq, 1 / downsampleFreq)
    # if downsampleQ == "n":

    # Iterate through each selected channel to export and verify
    for k in range(1, len(expFileInfo["Chs"]) + 1):
        if k != 1:
            # Arrange the data in a vector
            y = np.fromiter(convRawData[(k - 1) :: len(expFileInfo["Chs"])], float)
            print("\nThis is Ch", expFileInfo["Chs"][k - 1], " ")

            # visualize the reconstructed raw signal graphing To verify
            # plt.figure()
            # plt.plot(x, y, color="blue")
            # plt.title("Reconstructed Raw Signal")
            # plt.xlabel('(sec)')
            # plt.ylabel('uV')
            # plt.show()

            ##Metadata CSV export
            metadata_df = pd.DataFrame()
            metadata_df.attrs["Experiment Date-Time"] = ""
            metadata_df.attrs["Export Date-Time"] = datetime.datetime.now()
            metadata_df.attrs["Recorder"] = recorderName
            metadata_df.attrs["Channel"] = channelVerify
            metadata_df.attrs["Paradigm"] = paradigm
            metadata_df.attrs["Brain Region"] = brainRegion
            metadata_df.attrs["recLen"] = recLength
            metadata_df.attrs["Original Sampling Rate"] = OGsamplingRate
            metadata_df.attrs["Downsampling Rate"] = downsampleFreq

            attributes = pd.DataFrame.from_dict(
                metadata_df.attrs, orient="index", columns=["Value"]
            )

            # Adaptable name
            base = os.path.basename(fpath)
            csvName, extension = os.path.splitext(base)

            # Export metadata CSV
            folder_path = os.path.dirname(fpath) + "-" + csvName
            # folder_path = folder_path + csvName
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            metadata_file = os.path.join(folder_path, "metadata.csv")
            attributes.to_csv(metadata_file, index=True)

            ##Binary export
            format_string = "f" * len(x)
            binaryData = struct.pack(format_string, *y)
            bin_output_path = os.path.join(
                folder_path, str(expFileInfo["Chs"][k - 1]) + "_export.bin"
            )
            with open(bin_output_path, "wb") as binary_file:
                binary_file.write(binaryData)
    print("\nExporting complete.")

    return None


if __name__ == "__main__":
    main(fpath)
