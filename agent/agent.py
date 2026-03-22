import time
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import analyze_image, plot_navigation

def main():
    print("Initializing UNO Q Autonomy Agent...")
    print("Hardware Profile Target: Qualcomm Dragonwing MPU (Debian + llama.cpp)")
    
    # Initialize the LLM (connects to the local llama.cpp server instance)
    llm = ChatOpenAI(
        model="qwen2.5-vl", 
        base_url="http://localhost:11434/v1",
        api_key="sk-no-key-required",
        temperature=0.1
    )
    
    tools = [analyze_image, plot_navigation]
    
    # Initialize the modern LangGraph ReAct agent natively
    agent_executor = create_react_agent(llm, tools)
    
    print("Agent is initialized. Beginning control loop...")
    
    try:
        tick = 0
        while True:
            tick += 1
            print(f"\n--- New Agent Tick [{tick}] ---")
            
            # The overarching objective for the agent in this context
            objective = "Analyze the environment using the camera. If no dog is found, navigate forward slightly. Our goal is to find a dog."
            
            try:
                # Trigger the ReAct Observe -> Think -> Act loop using LangGraph messages state
                response = agent_executor.invoke({"messages": [("user", objective)]})
                
                # The final response is the last message content
                final_answer = response["messages"][-1].content
                print(f"Agent Action Loop Completed: {final_answer}")
            except Exception as e:
                print(f"Error in agent processing: {e}")
                
            # Simulate the internal serial / processing latency constraint of the actual hardware
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("Agent shutting down.")

if __name__ == "__main__":
    main()
