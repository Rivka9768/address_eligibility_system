from orchestrator import process_eligibility

def run_cli_test():
    print("--- מנוע בדיקת כתובות (הקלידי 'exit' או 'q' ליציאה) ---")
    
    while True:
        address = input("\nEnter address to test: ").strip()
        
        # תנאי יציאה מהלולאה
        if address.lower() in ['exit', 'q', 'quit']:
            print("יציאה מהבדיקה. להתראות!")
            break
            
        if not address:
            print("אנא הזיני כתובת תקפה.")
            continue

        result = process_eligibility(address)
        print(f"\nFinal Clean JSON Output:\n{result}")

if __name__ == "__main__":
    run_cli_test()