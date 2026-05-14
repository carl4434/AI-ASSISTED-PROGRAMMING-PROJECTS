import comtypes.client
import os

ModelPath =r"C:\Users\Carl\OneDrive\3 Projects\2612 TR AI ASSISTED SD\Day 2 0514\EATBS MODEL\CARYL BLDG_r5 Analysis.EDB"

if not os.path.exists(ModelPath):
    os.makedirs(ModelPath)

# Create API helper object

helper = comtypes.client.CreateObject('ETABSv1.Helper')
helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)

EtabsObject = helper.CreateObjectProgID("CSI.ETABS.API.ETABSObject")

# Start ETABS application
EtabsObject.ApplicationStart()

# Create SapModel object
SapModel = EtabsObject.SapModel
SapModel.InitializeNewModel

# Open and save the model
SapModel.File.OpenFile(ModelPath)

print("ETABS model opened successfully!")

# Get the model's name to verify the connection
ModelName = EtabsObject.SapModel.GetModelFilename()

# Print the model name
print(f"Model loaded: {ModelName}")

# Save model
SapModel.File.Save(ModelPath)

# Run the analysis
ret = SapModel.Analyze.RunAnalysis()

if ret == 0:
    print("Analysis completed successfully!")
else:
    print("Analysis failed.")

# Retrieve the list of all response combinations
ret, combinations, ret, cb = SapModel.RespCombo.GetNameList()

# Print all available combinations
print("Available combinations:", combinations)