import asyncio
from agent_reasoning import handle_user_query


async def main():
    # example user question
    query = "What courses do I have?"

    print("User:", query)

    # call the agent
    response = await handle_user_query(query)

    print("Agent:", response)


if __name__ == "__main__":
    asyncio.run(main())Update test_01_agent.py
