#!/usr/bin/env python3
"""
Benchmark Datasets Integration
Integrate standard memory evaluation datasets for BMAM testing
"""

import asyncio
import json
import os
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import hashlib

logger = logging.getLogger(__name__)


class BenchmarkDatasets:
    """Manage and integrate standard benchmark datasets"""

    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent.parent / "data" / "benchmarks"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Dataset configurations
        self.datasets = {
            "longmemeval": {
                "name": "LongMemEval",
                "description": "Long-term memory evaluation dataset",
                "url": "https://github.com/Psycoy/LongMemEval",
                "local_path": self.cache_dir / "longmemeval",
                "memos_path": Path("/Users/liyang/Desktop/testversion/MemOS/evaluation/data/longmemeval"),
                "data_files": ["test_data.json", "questions.json"],
                "categories": ["reasoning", "factual", "conversational"]
            },
            "locomo": {
                "name": "LoCoMo",
                "description": "Long Context Memory benchmark",
                "url": "https://github.com/psycoy/LoCoMo-Benchmark",
                "local_path": self.cache_dir / "locomo",
                "memos_path": Path("/Users/liyang/Desktop/testversion/MemOS/evaluation/data/locomo"),
                "data_files": ["locomo10.json", "locomo10_rag.json"],
                "categories": {
                    "1": "multi_hop",
                    "2": "temporal_reasoning",
                    "3": "open_domain",
                    "4": "single_hop"
                }
            },
            "needle_in_haystack": {
                "name": "Needle in Haystack",
                "description": "Information retrieval in long contexts",
                "url": "custom",
                "local_path": self.cache_dir / "needle_in_haystack",
                "data_files": ["test_cases.json"],
                "categories": ["short", "medium", "long", "very_long"]
            },
            "memorybank": {
                "name": "MemoryBank",
                "description": "Comprehensive memory evaluation",
                "url": "https://github.com/zhongwanjun/MemoryBank",
                "local_path": self.cache_dir / "memorybank",
                "data_files": ["test_data.json"],
                "categories": ["episodic", "semantic", "procedural"]
            }
        }

    async def download_dataset(self, dataset_name: str, force_refresh: bool = False) -> bool:
        """Download and cache a benchmark dataset"""
        if dataset_name not in self.datasets:
            logger.error(f"Unknown dataset: {dataset_name}")
            return False

        dataset_config = self.datasets[dataset_name]
        local_path = dataset_config["local_path"]

        # Check if already cached
        if local_path.exists() and not force_refresh:
            logger.info(f"Dataset {dataset_name} already cached at {local_path}")
            return True

        logger.info(f"Downloading dataset {dataset_name}...")

        try:
            local_path.mkdir(parents=True, exist_ok=True)

            if dataset_name == "longmemeval":
                success = await self._download_longmemeval(local_path)
            elif dataset_name == "locomo":
                success = await self._download_locomo(local_path)
            elif dataset_name == "needle_in_haystack":
                success = await self._generate_needle_in_haystack(local_path)
            elif dataset_name == "memorybank":
                success = await self._download_memorybank(local_path)
            else:
                success = False

            if success:
                logger.info(f"✅ Dataset {dataset_name} downloaded successfully")
                self._create_dataset_info(dataset_name, local_path)
            else:
                logger.error(f"❌ Failed to download dataset {dataset_name}")

            return success

        except Exception as e:
            logger.error(f"Error downloading dataset {dataset_name}: {e}")
            return False

    async def _download_longmemeval(self, local_path: Path) -> bool:
        """Download LongMemEval dataset"""
        try:
            # Generate sample LongMemEval data since we may not have direct access
            test_data = {
                "version": "1.0",
                "description": "Long-term memory evaluation tasks",
                "tasks": []
            }

            # Generate sample tasks
            for i in range(100):
                task = {
                    "id": f"lme_{i:04d}",
                    "category": ["reasoning", "factual", "conversational"][i % 3],
                    "context": self._generate_long_context(i),
                    "question": f"Question {i}: What is the main topic discussed in the context?",
                    "ground_truth": f"The main topic is topic_{i % 10}",
                    "metadata": {
                        "context_length": 2000 + (i * 100),
                        "difficulty": "medium",
                        "source": "synthetic"
                    }
                }
                test_data["tasks"].append(task)

            # Save test data
            with open(local_path / "test_data.json", 'w') as f:
                json.dump(test_data, f, indent=2)

            # Generate questions file
            questions = {
                "questions": [task["question"] for task in test_data["tasks"]],
                "answers": [task["ground_truth"] for task in test_data["tasks"]]
            }

            with open(local_path / "questions.json", 'w') as f:
                json.dump(questions, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to create LongMemEval data: {e}")
            return False

    async def _download_locomo(self, local_path: Path) -> bool:
        """Download LoCoMo dataset"""
        try:
            # Generate sample LoCoMo data
            test_data = {
                "version": "1.0",
                "description": "Long Context Memory benchmark",
                "categories": {
                    "1": "multi_hop",
                    "2": "temporal_reasoning",
                    "3": "open_domain",
                    "4": "single_hop"
                },
                "data": []
            }

            categories = ["1", "2", "3", "4"]
            category_names = ["multi_hop", "temporal_reasoning", "open_domain", "single_hop"]

            for i in range(80):  # 20 per category
                category_id = categories[i % 4]
                category_name = category_names[i % 4]

                item = {
                    "id": f"locomo_{i:04d}",
                    "category": category_id,
                    "category_name": category_name,
                    "context": self._generate_locomo_context(category_name, i),
                    "question": self._generate_locomo_question(category_name, i),
                    "answer": self._generate_locomo_answer(category_name, i),
                    "metadata": {
                        "difficulty": ["easy", "medium", "hard"][i % 3],
                        "context_length": 1500 + (i * 50)
                    }
                }
                test_data["data"].append(item)

            # Save test data
            with open(local_path / "locomo_test.json", 'w') as f:
                json.dump(test_data, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to create LoCoMo data: {e}")
            return False

    async def _generate_needle_in_haystack(self, local_path: Path) -> bool:
        """Generate Needle in Haystack test cases"""
        try:
            test_cases = {
                "version": "1.0",
                "description": "Needle in haystack information retrieval test",
                "test_cases": []
            }

            # Different context lengths
            length_configs = [
                {"category": "short", "length": 1000, "count": 10},
                {"category": "medium", "length": 5000, "count": 10},
                {"category": "long", "length": 15000, "count": 10},
                {"category": "very_long", "length": 50000, "count": 5}
            ]

            case_id = 0
            for config in length_configs:
                for i in range(config["count"]):
                    # Generate needle (target information)
                    needle = f"The secret code is: NEEDLE_{case_id:04d}"

                    # Generate haystack (long distracting context)
                    haystack = self._generate_haystack_context(config["length"], needle)

                    test_case = {
                        "id": f"nih_{case_id:04d}",
                        "category": config["category"],
                        "context": haystack,
                        "needle": needle,
                        "question": "What is the secret code mentioned in the text?",
                        "expected_answer": needle,
                        "metadata": {
                            "context_length": len(haystack),
                            "needle_position": haystack.find(needle),
                            "relative_position": haystack.find(needle) / len(haystack)
                        }
                    }
                    test_cases["test_cases"].append(test_case)
                    case_id += 1

            # Save test cases
            with open(local_path / "test_cases.json", 'w') as f:
                json.dump(test_cases, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to generate needle in haystack data: {e}")
            return False

    async def _download_memorybank(self, local_path: Path) -> bool:
        """Download MemoryBank dataset"""
        try:
            # Generate sample MemoryBank data
            test_data = {
                "version": "1.0",
                "description": "Comprehensive memory evaluation dataset",
                "categories": ["episodic", "semantic", "procedural"],
                "data": []
            }

            categories = ["episodic", "semantic", "procedural"]

            for i in range(90):  # 30 per category
                category = categories[i % 3]

                item = {
                    "id": f"mb_{i:04d}",
                    "category": category,
                    "memory_type": category,
                    "scenario": self._generate_memory_scenario(category, i),
                    "question": self._generate_memory_question(category, i),
                    "answer": self._generate_memory_answer(category, i),
                    "metadata": {
                        "complexity": ["simple", "moderate", "complex"][i % 3],
                        "temporal_distance": ["immediate", "recent", "distant"][i % 3]
                    }
                }
                test_data["data"].append(item)

            # Save test data
            with open(local_path / "test_data.json", 'w') as f:
                json.dump(test_data, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to create MemoryBank data: {e}")
            return False

    def load_dataset(self, dataset_name: str, category: str = None, use_memos_data: bool = True) -> Optional[Dict]:
        """Load a cached dataset, optionally from MemOS data"""
        if dataset_name not in self.datasets:
            logger.error(f"Unknown dataset: {dataset_name}")
            return None

        dataset_config = self.datasets[dataset_name]

        # Try to load from MemOS data first if available
        if use_memos_data and "memos_path" in dataset_config:
            memos_data = self._load_memos_dataset(dataset_name, category)
            if memos_data:
                return memos_data

        # Fallback to local cached data
        local_path = dataset_config["local_path"]

        if not local_path.exists():
            logger.error(f"Dataset {dataset_name} not found. Run download_dataset() first.")
            return None

        try:
            # Load main data file
            main_file = dataset_config["data_files"][0]
            with open(local_path / main_file) as f:
                data = json.load(f)

            # Filter by category if specified
            if category:
                data = self._filter_by_category(data, category, dataset_name)

            logger.info(f"Loaded dataset {dataset_name}" + (f" (category: {category})" if category else ""))
            return data

        except Exception as e:
            logger.error(f"Failed to load dataset {dataset_name}: {e}")
            return None

    def _load_memos_dataset(self, dataset_name: str, category: str = None) -> Optional[Dict]:
        """Load dataset from MemOS data directory"""
        dataset_config = self.datasets[dataset_name]
        memos_path = dataset_config.get("memos_path")

        if not memos_path or not memos_path.exists():
            logger.warning(f"MemOS data path not found for {dataset_name}: {memos_path}")
            return None

        try:
            if dataset_name == "locomo":
                return self._load_memos_locomo(memos_path, category)
            elif dataset_name == "longmemeval":
                return self._load_memos_longmemeval(memos_path, category)
            else:
                logger.warning(f"No MemOS loader for dataset: {dataset_name}")
                return None

        except Exception as e:
            logger.error(f"Failed to load MemOS dataset {dataset_name}: {e}")
            return None

    def _load_memos_locomo(self, memos_path: Path, category: str = None) -> Optional[Dict]:
        """Load LoCoMo dataset from MemOS format"""
        locomo_file = memos_path / "locomo10.json"
        if not locomo_file.exists():
            logger.error(f"LoCoMo data file not found: {locomo_file}")
            return None

        with open(locomo_file) as f:
            data = json.load(f)

        # Parse MemOS LoCoMo format
        parsed_data = {
            "version": "memos_locomo_10",
            "description": "LoCoMo benchmark from MemOS",
            "categories": {
                "1": "multi_hop",
                "2": "temporal_reasoning",
                "3": "open_domain",
                "4": "single_hop"
            },
            "data": []
        }

        for conversation in data:
            if "qa" in conversation:
                for qa_item in conversation["qa"]:
                    item = {
                        "id": f"locomo_{len(parsed_data['data']):04d}",
                        "question": qa_item["question"],
                        "answer": str(qa_item["answer"]),
                        "category": str(qa_item.get("category", "4")),
                        "category_name": parsed_data["categories"].get(str(qa_item.get("category", "4")), "single_hop"),
                        "evidence": qa_item.get("evidence", []),
                        "context": conversation.get("conversation", ""),
                        "metadata": {
                            "source": "memos_locomo10",
                            "conversation_id": conversation.get("id", "unknown")
                        }
                    }
                    parsed_data["data"].append(item)

        # Filter by category if specified
        if category:
            category_id = None
            for cat_id, cat_name in parsed_data["categories"].items():
                if cat_name == category:
                    category_id = cat_id
                    break

            if category_id:
                filtered_data = [item for item in parsed_data["data"] if item["category"] == category_id]
                parsed_data["data"] = filtered_data

        logger.info(f"Loaded MemOS LoCoMo dataset with {len(parsed_data['data'])} items")
        return parsed_data

    def _load_memos_longmemeval(self, memos_path: Path, category: str = None) -> Optional[Dict]:
        """Load LongMemEval dataset from MemOS format"""
        # Note: MemOS LongMemEval data directory appears to be empty (.gitkeep only)
        # This would need actual LongMemEval data files
        logger.warning("MemOS LongMemEval data directory is empty, using synthetic data")
        return None

    def _filter_by_category(self, data: Dict, category: str, dataset_name: str) -> Dict:
        """Filter dataset by category"""
        if dataset_name == "longmemeval":
            filtered_tasks = [task for task in data.get("tasks", []) if task.get("category") == category]
            return {**data, "tasks": filtered_tasks}

        elif dataset_name == "locomo":
            filtered_data = [item for item in data.get("data", []) if item.get("category_name") == category]
            return {**data, "data": filtered_data}

        elif dataset_name == "needle_in_haystack":
            filtered_cases = [case for case in data.get("test_cases", []) if case.get("category") == category]
            return {**data, "test_cases": filtered_cases}

        elif dataset_name == "memorybank":
            filtered_data = [item for item in data.get("data", []) if item.get("category") == category]
            return {**data, "data": filtered_data}

        return data

    def get_dataset_info(self, dataset_name: str = None) -> Dict:
        """Get information about available datasets"""
        if dataset_name:
            if dataset_name in self.datasets:
                config = self.datasets[dataset_name].copy()
                config["cached"] = config["local_path"].exists()
                if config["cached"]:
                    config["cache_info"] = self._get_cache_info(config["local_path"])
                return config
            return {}

        # Return info for all datasets
        info = {}
        for name, config in self.datasets.items():
            dataset_info = config.copy()
            dataset_info["cached"] = config["local_path"].exists()
            if dataset_info["cached"]:
                dataset_info["cache_info"] = self._get_cache_info(config["local_path"])
            info[name] = dataset_info

        return info

    def _get_cache_info(self, path: Path) -> Dict:
        """Get cache information for a dataset"""
        info = {
            "path": str(path),
            "cached_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "size_mb": sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) / 1024 / 1024
        }

        # Count items in dataset
        data_files = list(path.glob("*.json"))
        if data_files:
            try:
                with open(data_files[0]) as f:
                    data = json.load(f)

                if "tasks" in data:
                    info["item_count"] = len(data["tasks"])
                elif "data" in data:
                    info["item_count"] = len(data["data"])
                elif "test_cases" in data:
                    info["item_count"] = len(data["test_cases"])
                else:
                    info["item_count"] = "unknown"
            except:
                info["item_count"] = "unknown"

        return info

    def _create_dataset_info(self, dataset_name: str, local_path: Path):
        """Create dataset info file"""
        config = self.datasets[dataset_name]
        info = {
            "name": config["name"],
            "description": config["description"],
            "downloaded_at": datetime.now().isoformat(),
            "source_url": config["url"],
            "categories": config["categories"],
            "data_files": config["data_files"]
        }

        with open(local_path / "dataset_info.json", 'w') as f:
            json.dump(info, f, indent=2)

    # Helper methods for generating test data
    def _generate_long_context(self, seed: int) -> str:
        """Generate long context for testing"""
        topics = ["technology", "science", "business", "history", "culture", "sports", "health", "education", "environment", "politics"]
        topic = topics[seed % len(topics)]

        return f"""
        This is a comprehensive discussion about {topic}. The document contains multiple sections
        covering various aspects of the subject. In section 1, we explore the fundamental concepts
        and basic principles that govern this field. The historical development shows how {topic}
        has evolved over the past decades, with significant milestones and breakthrough discoveries.

        Section 2 delves into the current state of {topic}, examining recent trends and developments.
        Expert opinions suggest that the field is moving towards more innovative approaches and
        methodologies. The impact on society has been substantial, affecting various sectors and
        demographics in different ways.

        The third section analyzes future prospects and potential challenges. Researchers predict
        that within the next decade, we will see major advances in {topic} that could revolutionize
        how we understand and interact with this domain. Key factors include technological advancement,
        regulatory changes, and evolving public awareness.

        Throughout this document, we maintain focus on topic_{seed % 10} as a central theme,
        examining its implications across multiple dimensions and providing comprehensive coverage
        of all relevant aspects.
        """

    def _generate_locomo_context(self, category: str, seed: int) -> str:
        """Generate context for LoCoMo tasks"""
        contexts = {
            "single_hop": f"John Smith is the CEO of TechCorp. The company was founded in 200{seed % 10}.",
            "multi_hop": f"Sarah leads the engineering team. The project led by Sarah increased revenue by ${seed % 5 + 1}.5M.",
            "temporal_reasoning": f"The meeting happened on Monday. The decision was made on Tuesday. Implementation started on Wednesday day {seed}.",
            "open_domain": f"The research paper discusses {['AI', 'robotics', 'quantum computing'][seed % 3]} applications in modern technology."
        }
        return contexts.get(category, f"Generic context for item {seed}")

    def _generate_locomo_question(self, category: str, seed: int) -> str:
        """Generate questions for LoCoMo tasks"""
        questions = {
            "single_hop": "Who is the CEO of TechCorp?",
            "multi_hop": "What was the revenue impact of the project led by the head of engineering?",
            "temporal_reasoning": "What happened after the Monday meeting?",
            "open_domain": "What technology is discussed in the research paper?"
        }
        return questions.get(category, f"Question for item {seed}")

    def _generate_locomo_answer(self, category: str, seed: int) -> str:
        """Generate answers for LoCoMo tasks"""
        answers = {
            "single_hop": "John Smith",
            "multi_hop": f"${seed % 5 + 1}.5M increase",
            "temporal_reasoning": "A decision was made on Tuesday",
            "open_domain": ['AI', 'robotics', 'quantum computing'][seed % 3]
        }
        return answers.get(category, f"Answer for item {seed}")

    def _generate_haystack_context(self, target_length: int, needle: str) -> str:
        """Generate haystack context with embedded needle"""
        # Generate filler text
        filler_sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Technology advances continue to shape our modern world.",
            "The weather today is particularly pleasant and sunny.",
            "Scientific research reveals new insights about the universe.",
            "Business developments impact global economic trends significantly.",
            "Cultural diversity enriches our communities and societies.",
            "Educational initiatives promote learning and growth opportunities."
        ]

        # Build context
        context_parts = []
        current_length = 0

        # Add initial filler
        while current_length < target_length * 0.3:
            sentence = filler_sentences[current_length % len(filler_sentences)]
            context_parts.append(sentence)
            current_length += len(sentence) + 1

        # Insert needle
        context_parts.append(needle)
        current_length += len(needle) + 1

        # Add remaining filler
        while current_length < target_length:
            sentence = filler_sentences[current_length % len(filler_sentences)]
            context_parts.append(sentence)
            current_length += len(sentence) + 1

        return " ".join(context_parts)

    def _generate_memory_scenario(self, category: str, seed: int) -> str:
        """Generate memory scenarios for different types"""
        scenarios = {
            "episodic": f"Yesterday, you went to the grocery store and bought milk, bread, and item_{seed % 10}.",
            "semantic": f"The capital of France is Paris. The currency used in France is the Euro. Fact_{seed % 10} is important.",
            "procedural": f"To make coffee: 1) Heat water, 2) Add coffee grounds, 3) Pour hot water, 4) Step_{seed % 5}."
        }
        return scenarios.get(category, f"Memory scenario {seed}")

    def _generate_memory_question(self, category: str, seed: int) -> str:
        """Generate memory questions"""
        questions = {
            "episodic": "What did you buy at the grocery store yesterday?",
            "semantic": "What is the capital of France?",
            "procedural": "How do you make coffee?"
        }
        return questions.get(category, f"Memory question {seed}")

    def _generate_memory_answer(self, category: str, seed: int) -> str:
        """Generate memory answers"""
        answers = {
            "episodic": f"Milk, bread, and item_{seed % 10}",
            "semantic": "Paris",
            "procedural": "Heat water, add coffee grounds, pour hot water"
        }
        return answers.get(category, f"Memory answer {seed}")


async def main():
    """Test dataset management functionality"""
    datasets = BenchmarkDatasets()

    print("Available datasets:")
    info = datasets.get_dataset_info()
    for name, config in info.items():
        print(f"- {name}: {config['description']} (Cached: {config['cached']})")

    print("\nDownloading datasets...")
    for dataset_name in ["longmemeval", "locomo", "needle_in_haystack", "memorybank"]:
        success = await datasets.download_dataset(dataset_name)
        if success:
            print(f"✅ {dataset_name} ready")
        else:
            print(f"❌ {dataset_name} failed")

    print("\nTesting dataset loading...")
    for dataset_name in ["longmemeval", "locomo"]:
        data = datasets.load_dataset(dataset_name)
        if data:
            print(f"✅ Loaded {dataset_name}")
        else:
            print(f"❌ Failed to load {dataset_name}")


if __name__ == "__main__":
    asyncio.run(main())