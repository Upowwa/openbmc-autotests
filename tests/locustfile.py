from locust import HttpUser, task, between

class OpenBMCAPI(HttpUser):
    wait_time = between(1, 3)
    host = "https://localhost:2443" 

    @task(2)
    def get_system_info(self):
        self.client.get("/redfish/v1/Systems/system", auth=("root", "0penBmc"), verify=False, name="System info")

    @task(1)
    def get_power_state(self):
        response = self.client.get("/redfish/v1/Systems/system", auth=("root", "0penBmc"), verify=False, name="PowerState")
        if response.status_code == 200:
            power_state = response.json().get("PowerState")

class PublicAPI(HttpUser):
    wait_time = between(1, 3)

    @task(1)
    def get_weather(self):
        self.client.get("https://wttr.in/Novosibirsk?format=j1")


