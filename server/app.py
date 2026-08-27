from fastapi import FastAPI, Request
import json

app = FastAPI()

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "message": "Server is up and running healthy"
    }

@app.post("/api/sensor")
async def collect_sensor_data(req: Request):
    try:
        body = await req.json()
        #save the data in a file 
        with open("sensor_data.json", "a") as f:
            json.dump(body, f)

        print("Data received: ", body)
        return {"message": "Sensor data received successfully", "Data : " : body}
    except Exception as e:
        return {"status": "error", "message": "Failed to parse sensor data"}  

@app.get("/api/sensor")
def get_sensor_data():
    with open("sensor_data.json", "r") as f:
        return json.load(f)