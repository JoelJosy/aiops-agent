import random
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    # Random wait time between requests 
    wait_time = between(0.5, 2.0)  

    def on_start(self):
        self.item_ids = []
        # Create an initial item when user start
        self.create_item()  

    @task(weight=2)
    def create_item(self):
        # 20% chance to create a new item
        item_data = {
            "name": f"Item {random.randint(1000, 9999)}",
            "price": round(random.uniform(10.0, 500.0), 2)
        }

        with self.client.post("/items", json=item_data, catch_response=True) as response:
            if response.status_code == 201:
                item_id = response.json().get("id")
                if item_id:
                    self.item_ids.append(item_id)
                    # Cap list to most recent 50 items
                    if len(self.item_ids) > 50:
                        self.item_ids = self.item_ids[-50:]
            else:
                response.failure(f"Failed to create item: {response.text}")

    @task(weight=8)
    def get_item(self):
        # 80% requests get an existing item
        if not self.item_ids:
            return  # Early exit if no items exist yet
        item_id = random.choice(self.item_ids)
        self.client.get(f"/items/{item_id}")