#!/usr/bin/env python3
"""
MBTI Personality System Demo
MBTI人格系统演示

This script demonstrates how to use the MBTI-based personality system
with different personality types and configurations.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.core.mbti_integration import create_mbti_personality_system, get_available_personalities
from agents.core.mbti_personality import MBTIType
from agents.base import AgentMessage, MessageType


class MBTIDemo:
    """Demo class for MBTI personality system"""

    def __init__(self):
        self.system = None
        self.demo_conversations = {
            "INTJ": [
                "How should I approach learning a new programming language?",
                "What's the most efficient way to organize a software project?",
                "Can you help me plan a strategy for career advancement?"
            ],
            "ENFP": [
                "I'm feeling stuck and need some creative inspiration!",
                "What are some fun ways to meet new people?",
                "I have so many ideas but struggle to focus on one - help!"
            ],
            "ISTP": [
                "My computer is running slowly, what should I do?",
                "I need to fix a leaky faucet - got any tips?",
                "What's the best way to learn hands-on skills?"
            ],
            "ESFJ": [
                "How can I help my friend who's going through a tough time?",
                "I'm organizing a team event - what should I consider?",
                "How do I handle conflict in a group setting?"
            ]
        }

    async def initialize_system(self):
        """Initialize the MBTI personality system"""
        print("🧠 Initializing MBTI Personality System...")

        self.system = create_mbti_personality_system(
            initial_personality="INTJ",
            name="MBTI Demo Assistant"
        )

        print("✅ System initialized!")
        return True

    async def show_available_personalities(self):
        """Show all available personality types"""
        print("\n📋 Available MBTI Personality Types:")
        print("=" * 60)

        personalities = get_available_personalities()

        for personality in personalities:
            print(f"🏷️  {personality['type']} - {personality['title']}")
            print(f"    {personality['description']}")
            print(f"    Key traits: {', '.join(personality['traits'])}")
            print()

    async def demonstrate_personality_switching(self):
        """Demonstrate switching between different personality types"""
        print("\n🔄 Demonstrating Personality Switching")
        print("=" * 60)

        # Test different personalities
        test_personalities = ["INTJ", "ENFP", "ISTP", "ESFJ"]
        user_question = "I'm working on a complex project and feeling overwhelmed. How should I approach this?"

        for personality_type in test_personalities:
            print(f"\n🎭 Switching to {personality_type}...")

            # Switch personality
            switch_message = AgentMessage(
                sender_id="demo",
                recipient_id="mbti_system",
                message_type=MessageType.REQUEST,
                content={
                    'action': 'mbti_switch_personality',
                    'personality_type': personality_type
                }
            )

            switch_result = await self.system.process_message(switch_message)

            if switch_result.get('success'):
                print(f"✅ Successfully switched to {personality_type}")
                print(f"   {switch_result.get('message', '')}")

                # Get response with this personality
                response_message = AgentMessage(
                    sender_id="demo",
                    recipient_id="mbti_system",
                    message_type=MessageType.REQUEST,
                    content={
                        'action': 'generate_personality_response',
                        'user_input': user_question
                    }
                )

                response = await self.system.process_message(response_message)

                print(f"\n💬 {personality_type} Response:")
                print(f"   {response.get('response', 'No response available')}")

            else:
                print(f"❌ Failed to switch to {personality_type}: {switch_result.get('message', 'Unknown error')}")

    async def demonstrate_personality_conversations(self):
        """Demonstrate conversations tailored to each personality type"""
        print("\n💬 Personality-Specific Conversations")
        print("=" * 60)

        for personality_type, questions in self.demo_conversations.items():
            print(f"\n🎭 {personality_type} Conversation Demo:")

            # Switch to personality
            switch_message = AgentMessage(
                sender_id="demo",
                recipient_id="mbti_system",
                message_type=MessageType.REQUEST,
                content={
                    'action': 'mbti_switch_personality',
                    'personality_type': personality_type
                }
            )

            await self.system.process_message(switch_message)

            # Ask questions
            for question in questions:
                print(f"\n❓ User: {question}")

                response_message = AgentMessage(
                    sender_id="demo",
                    recipient_id="mbti_system",
                    message_type=MessageType.REQUEST,
                    content={
                        'action': 'generate_personality_response',
                        'user_input': question
                    }
                )

                response = await self.system.process_message(response_message)
                print(f"🤖 {personality_type}: {response.get('response', 'No response')}")

    async def demonstrate_personality_comparison(self):
        """Demonstrate personality type comparison"""
        print("\n🔍 Personality Type Comparison")
        print("=" * 60)

        # Compare INTJ vs ENFP
        comparison_message = AgentMessage(
            sender_id="demo",
            recipient_id="mbti_system",
            message_type=MessageType.REQUEST,
            content={
                'action': 'mbti_compare_types',
                'type1': 'INTJ',
                'type2': 'ENFP'
            }
        )

        comparison = await self.system.process_message(comparison_message)

        if 'comparison' in comparison:
            print("\n📊 INTJ vs ENFP Comparison:")

            for type_name, details in comparison['comparison'].items():
                print(f"\n{type_name} - {details['title']}:")
                print(f"  Description: {details['description']}")
                print(f"  Strengths: {', '.join(details['strengths'])}")
                print(f"  Dominant Function: {details['dominant_function']}")

            print(f"\n🔑 Key Differences:")
            for diff in comparison.get('key_differences', []):
                print(f"  • {diff}")

    async def demonstrate_configuration(self):
        """Demonstrate system configuration"""
        print("\n⚙️ System Configuration Demo")
        print("=" * 60)

        # Get current configuration
        info_message = AgentMessage(
            sender_id="demo",
            recipient_id="mbti_system",
            message_type=MessageType.REQUEST,
            content={'action': 'mbti_get_info'}
        )

        info = await self.system.process_message(info_message)

        print("📋 Current Configuration:")
        config = info.get('configuration', {})

        print(f"  Current Personality: {config.get('current_personality', {}).get('type', 'Unknown')}")
        print(f"  Mode: {config.get('mode', 'Unknown')}")

        settings = config.get('settings', {})
        print(f"  Allow Switching: {settings.get('allow_switching', False)}")
        print(f"  Auto Detection: {settings.get('auto_detect', False)}")

        # Demonstrate configuration change
        print("\n🔧 Updating Configuration...")

        config_message = AgentMessage(
            sender_id="demo",
            recipient_id="mbti_system",
            message_type=MessageType.REQUEST,
            content={
                'action': 'mbti_configure',
                'settings': {
                    'auto_detect_preference': True,
                    'formality_adjustment': 0.1
                }
            }
        )

        config_result = await self.system.process_message(config_message)
        print(f"✅ Configuration update: {config_result.get('message', 'No message')}")

    async def demonstrate_session_stats(self):
        """Demonstrate session statistics"""
        print("\n📊 Session Statistics")
        print("=" * 60)

        stats_message = AgentMessage(
            sender_id="demo",
            recipient_id="mbti_system",
            message_type=MessageType.REQUEST,
            content={'action': 'mbti_get_stats'}
        )

        stats = await self.system.process_message(stats_message)

        print(f"🕒 Session Duration: {stats.get('session_duration_formatted', 'Unknown')}")
        print(f"💬 Total Interactions: {stats.get('interactions', 0)}")
        print(f"🔄 Personality Switches: {stats.get('personality_switches', 0)}")

        usage = stats.get('personality_usage', {})
        if usage:
            print(f"\n📈 Personality Usage:")
            for personality, count in usage.items():
                print(f"  {personality}: {count} interactions")

        distribution = stats.get('personality_distribution', {})
        if distribution:
            print(f"\n📊 Usage Distribution:")
            for personality, percentage in distribution.items():
                print(f"  {personality}: {percentage:.1f}%")

    async def demonstrate_health_check(self):
        """Demonstrate system health check"""
        print("\n🏥 System Health Check")
        print("=" * 60)

        health = self.system.get_system_health()

        print(f"🔍 Overall Status: {health.get('overall_status', 'Unknown')}")
        print(f"🤖 MBTI Agent: {health.get('mbti_agent_status', 'Unknown')}")
        print(f"🔄 Fallback Agent: {health.get('fallback_agent_status', 'Unknown')}")
        print(f"⚙️ Configuration: {health.get('configuration_status', 'Unknown')}")

        current_personality = health.get('current_personality', {})
        if current_personality:
            print(f"\n🎭 Current Personality:")
            print(f"  Type: {current_personality.get('type', 'Unknown')}")
            print(f"  Interactions: {current_personality.get('interaction_count', 0)}")

        errors = health.get('errors', [])
        if errors:
            print(f"\n⚠️ Errors:")
            for error in errors:
                print(f"  • {error}")

    async def run_full_demo(self):
        """Run the complete demo"""
        print("🚀 MBTI Personality System - Complete Demo")
        print("=" * 80)

        # Initialize
        await self.initialize_system()

        # Run demo sections
        await self.show_available_personalities()
        await self.demonstrate_personality_switching()
        await self.demonstrate_personality_conversations()
        await self.demonstrate_personality_comparison()
        await self.demonstrate_configuration()
        await self.demonstrate_session_stats()
        await self.demonstrate_health_check()

        print("\n✨ Demo completed successfully!")
        print("The MBTI personality system is ready for integration.")

    async def interactive_demo(self):
        """Run interactive demo"""
        print("🎮 MBTI Personality System - Interactive Demo")
        print("=" * 60)

        await self.initialize_system()

        while True:
            print("\n📋 Demo Options:")
            print("1. Show available personalities")
            print("2. Switch personality")
            print("3. Have a conversation")
            print("4. Compare personalities")
            print("5. View configuration")
            print("6. View session stats")
            print("7. System health check")
            print("8. Run full demo")
            print("0. Exit")

            choice = input("\n🎯 Select option (0-8): ").strip()

            if choice == '0':
                break
            elif choice == '1':
                await self.show_available_personalities()
            elif choice == '2':
                await self._interactive_personality_switch()
            elif choice == '3':
                await self._interactive_conversation()
            elif choice == '4':
                await self._interactive_comparison()
            elif choice == '5':
                await self.demonstrate_configuration()
            elif choice == '6':
                await self.demonstrate_session_stats()
            elif choice == '7':
                await self.demonstrate_health_check()
            elif choice == '8':
                await self.run_full_demo()
            else:
                print("❌ Invalid choice. Please try again.")

        print("👋 Demo ended. Thank you!")

    async def _interactive_personality_switch(self):
        """Interactive personality switching"""
        print("\n🎭 Personality Switching")

        personality_type = input("Enter personality type (e.g., INTJ, ENFP): ").strip().upper()

        switch_message = AgentMessage(
            sender_id="demo",
            recipient_id="mbti_system",
            message_type=MessageType.REQUEST,
            content={
                'action': 'mbti_switch_personality',
                'personality_type': personality_type
            }
        )

        result = await self.system.process_message(switch_message)

        if result.get('success'):
            print(f"✅ {result.get('message', 'Success')}")
        else:
            print(f"❌ {result.get('message', 'Failed')}")

    async def _interactive_conversation(self):
        """Interactive conversation"""
        print("\n💬 Conversation with Current Personality")

        question = input("Ask a question: ").strip()

        if question:
            response_message = AgentMessage(
                sender_id="demo",
                recipient_id="mbti_system",
                message_type=MessageType.REQUEST,
                content={
                    'action': 'generate_personality_response',
                    'user_input': question
                }
            )

            response = await self.system.process_message(response_message)
            print(f"\n🤖 Response: {response.get('response', 'No response available')}")

    async def _interactive_comparison(self):
        """Interactive personality comparison"""
        print("\n🔍 Personality Comparison")

        type1 = input("Enter first personality type: ").strip().upper()
        type2 = input("Enter second personality type: ").strip().upper()

        comparison_message = AgentMessage(
            sender_id="demo",
            recipient_id="mbti_system",
            message_type=MessageType.REQUEST,
            content={
                'action': 'mbti_compare_types',
                'type1': type1,
                'type2': type2
            }
        )

        comparison = await self.system.process_message(comparison_message)

        if 'error' in comparison:
            print(f"❌ {comparison['error']}")
        else:
            print(f"\n📊 {type1} vs {type2} Comparison:")
            for diff in comparison.get('key_differences', []):
                print(f"  • {diff}")


async def main():
    """Main demo function"""
    demo = MBTIDemo()

    # Choose demo mode
    print("🧠 MBTI Personality System Demo")
    print("1. Full automated demo")
    print("2. Interactive demo")

    choice = input("\nSelect mode (1-2): ").strip()

    if choice == '1':
        await demo.run_full_demo()
    elif choice == '2':
        await demo.interactive_demo()
    else:
        print("❌ Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())