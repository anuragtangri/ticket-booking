import time
import threading,requests

FLASK_URL = "http://127.0.0.1:5000"

def make_booking(thread_id):
    """
    Sends a POST request to the booking endpoint with unique data.
    """
    try:
        data = {
            "name": f"Thread-{thread_id}",
            "date": "2025-08-06"
        }
        response = requests.post(f"{FLASK_URL}/booking", json=data)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Thread {thread_id}: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Thread {thread_id} failed to connect: {e}")
    except Exception as e:
        print(f"Thread {thread_id} encountered an error: {e}")


if __name__=="__main__":
    num_threads=100
    threads=[]
    time.sleep(5)

    start_time=time.time()

    for i in range(num_threads):
        thread = threading.Thread(target=make_booking, args=(i,))
        threads.append(thread)
        thread.start()
    
    for t in threads:
        t.join()
    
    end_time=time.time()
    print(f"\nAll {num_threads} booking attempts completed in {end_time - start_time:.2f} seconds.")
    print("Check the seat matrix at http://127.0.0.1:5000/booking/show to see the results.")