from fastapi import FastAPI, Request

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
        print("Data received: ", body)
        return {"message": "Sensor data received successfully", "Data : " : body}
    except Exception as e:
        return {"status": "error", "message": "Failed to parse sensor data"}  