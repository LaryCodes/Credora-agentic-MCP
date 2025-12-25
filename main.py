"""Main entry point for the Credora CFO Agent system.

This module initializes all agents with proper configuration and provides
both programmatic and CLI interfaces for interacting with the CFO Agent.

Requirements: 6.6, 5.4
"""

import os
import asyncio
import sys
from typing import Optional

from dotenv import load_dotenv
from agents import Runner, set_tracing_disabled

from credora.agents import (
    create_cfo_agent,
    get_default_model,
)
from credora.state import StateManager
from credora.examples import (
    EXAMPLE_QUERIES,
    get_examples_by_category,
    get_all_categories,
    print_examples,
)


# Load environment variables
load_dotenv()


# Disable tracing for cleaner output
set_tracing_disabled(disabled=True)


# Global state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the global state manager instance.
    
    Returns:
        StateManager instance
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


async def run_conversation(user_input: str, user_id: str = "default_user") -> str:
    """Run a single conversation turn with the CFO Agent.
    
    Args:
        user_input: The user's message
        user_id: The user identifier for session management
        
    Returns:
        The agent's response
        
    Requirements: 6.6
    """
    # Create CFO agent with all handoffs configured
    cfo_agent = create_cfo_agent()
    
    # Run the agent
    result = await Runner.run(
        cfo_agent,
        input=user_input,
    )
    
    return result.final_output


async def run_interactive_session(user_id: str = "default_user") -> None:
    """Run an interactive CLI session with the CFO Agent.
    
    Provides a simple command-line interface for testing conversations.
    
    Args:
        user_id: The user identifier for session management
        
    Requirements: 5.4
    """
    print("\n" + "=" * 60)
    print("  Credora CFO Agent - Interactive Session")
    print("=" * 60)
    print("\nWelcome! I'm your AI-powered CFO assistant.")
    print("Type 'quit' or 'exit' to end the session.")
    print("Type 'help' to see example queries.")
    print("-" * 60 + "\n")
    
    # Create CFO agent
    cfo_agent = create_cfo_agent()
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ("quit", "exit", "q"):
                print("\nThank you for using Credora CFO Agent. Goodbye!")
                break
            
            # Check for help command
            if user_input.lower() == "help":
                print_help()
                continue
            
            # Check for examples command
            if user_input.lower() == "examples":
                print_examples()
                continue
            
            # Run the agent
            print("\nCFO Agent: ", end="", flush=True)
            result = await Runner.run(
                cfo_agent,
                input=user_input,
            )
            print(result.final_output)
            print()
            
        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.\n")


def print_help() -> None:
    """Print help information with example queries."""
    print("\n" + "-" * 60)
    print("Example Queries:")
    print("-" * 60)
    
    # Use the examples module
    print_examples()
    
    print("\nCommands:")
    print("  help     - Show this help message")
    print("  examples - Show all example queries")
    print("  quit     - Exit the session")
    print("-" * 60 + "\n")


async def run_example_queries() -> None:
    """Run example queries demonstrating each agent capability.
    
    This function demonstrates the CFO Agent's ability to route
    queries to appropriate specialized agents.
    
    Requirements: 5.4
    """
    print("\n" + "=" * 60)
    print("  Credora CFO Agent - Example Queries Demo")
    print("=" * 60 + "\n")
    
    # Select one example from each category
    categories = get_all_categories()
    selected_examples = []
    
    for category in sorted(categories):
        examples = get_examples_by_category(category)
        if examples:
            selected_examples.append(examples[0])
    
    cfo_agent = create_cfo_agent()
    
    for example in selected_examples:
        print(f"\n[{example.category}] {example.description}")
        print(f"Query: {example.query}")
        print(f"Expected Agent: {example.expected_agent}")
        print("-" * 50)
        
        try:
            result = await Runner.run(
                cfo_agent,
                input=example.query,
            )
            response = result.final_output
            # Truncate long responses for demo
            if len(response) > 500:
                print(f"Response: {response[:500]}...")
                print("(truncated)")
            else:
                print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")
        
        print()


async def main() -> None:
    """Main entry point for the Credora CFO Agent.
    
    Supports multiple modes:
    - Interactive CLI session (default)
    - Example queries demo (--demo flag)
    - Single query (--query "your query")
    
    Requirements: 6.6
    """
    # Parse command line arguments
    args = sys.argv[1:]
    
    if "--demo" in args:
        # Run example queries demo
        await run_example_queries()
    elif "--query" in args:
        # Run single query
        try:
            query_idx = args.index("--query") + 1
            if query_idx < len(args):
                query = args[query_idx]
                response = await run_conversation(query)
                print(f"Response: {response}")
            else:
                print("Error: --query requires a query string")
                sys.exit(1)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        # Run interactive session
        await run_interactive_session()


if __name__ == "__main__":
    asyncio.run(main())
