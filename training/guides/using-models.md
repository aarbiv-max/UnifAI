before using the models in Genie there a few steps needed to be done
1. register adapter/s
2. unload the current model from the GPU
3. load the new adapter using the same base model


**register adapters**

```
curl --location 'http://bastion.8jlcp.sandbox586.opentlc.com:8002/api/backend/registerAdapter' \
--header 'Content-Type: application/json' \
--data '{"repoId": "<repo id in huggingface>","epoch": <epoch number>,"checkpointStep": <checkpoint file number for the selected epoch>}
```
```
curl --location 'http://bastion.8jlcp.sandbox586.opentlc.com:8002/api/backend/registerAdapter' \
--header 'Content-Type: application/json' \
--data '{"repoId": "taguser/microshift-epoch10-2025-Mar-27","epoch": 5,"checkpointStep": 195}
```
when registering the adapters you'll need both epoch and the checkpoint ID as we're not sure if the lowest epoch file exists so we ask the user for both
in order to know the desired checkpoint you'll need to know what epoch you want and find the lowest checkpoint file (this is epoch #1)
then you multiply the lowest checkpoint number * required_epochs 

reponse:
{"uid": "67d82fcf2870102f0469e2f8", "base_model": "Qwen/Qwen2.5-Coder-14B-Instruct", "adapter": "microshift-10-2025-Mar-27-epoch5", "adapter_uid": "d8bccc76-2f25-402f-b178-85a593e083b0", "quantized": true, "model_type": "finetuned", "context_length": 22000}


**unload model**

the call below will unload the current model from the GPU
```
curl --location 'http://bastion.8jlcp.sandbox586.opentlc.com:8002/api/backend/unloadModel'
```
**load the adapter**

this call below will load to the GPU the base model for the adapter we specify along with the adapter specified.
```
curl --location 'http://bastion.8jlcp.sandbox586.opentlc.com:8002/api/backend/loadModel?adapterId=11ac234d-2bb7-49cd-b153-e696ff4f9138'
```
the adapter ID is the same as from the register model call