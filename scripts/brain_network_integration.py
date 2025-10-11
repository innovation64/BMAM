"""
这是要添加到brain_coordinator.py的_process_with_brain_network方法
插入位置: 第1658行之前
"""

METHOD_CODE = '''
    async def _process_with_brain_network(
        self,
        user_input: str,
        context: Dict[str, Any],
        start_time: datetime
    ) -> ProcessingResult:
        """
        使用BrainNetwork图拓扑 + CapabilityOrchestrator处理输入

        流程:
        1. CapabilityAnalyzer分析需要的推理能力
        2. 记忆检索 (带时间范围过滤)
        3. 分布式记忆分配到脑区
        4. CapabilityOrchestrator编排推理 OR BrainNetwork激活扩散
        """
        # 步骤1: 语言检测
        perception_result = await self._activate_agent(
            'perception_encoding',
            AgentMessage(
                sender='coordinator',
                receiver='perception_encoding',
                message_type='request',
                content={'action': 'detect_language', 'text': user_input}
            )
        )

        detected_language = perception_result.get('language', 'en')
        language_confidence = perception_result.get('confidence', 0.9)
        context['detected_language'] = detected_language
        context['language_confidence'] = language_confidence

        logger.info(f"🌐 Detected language: {detected_language} (confidence: {language_confidence:.2f})")

        # 🔥 步骤2: 使用CapabilityAnalyzer分析推理能力
        from src.reasoning.capability_analyzer import CapabilityAnalyzer
        analyzer = CapabilityAnalyzer()

        try:
            capability_analysis = await analyzer.analyze(user_input)
            capabilities = capability_analysis.get('capabilities', [])
            execution_plan = capability_analysis.get('execution_plan', 'Sequential execution')

            logger.info(f"🧠 Detected capabilities: {[c['name'] for c in capabilities]}")
            logger.info(f"📋 Execution plan: {execution_plan}")

            # 简化的复杂度检测
            if len(capabilities) == 0:
                complexity_level = 0
                max_iterations = 0
            elif len(capabilities) <= 2 and not any(c['name'] == 'multi_hop_inference' for c in capabilities):
                complexity_level = 1
                max_iterations = 1
            elif len(capabilities) <= 3:
                complexity_level = 2
                max_iterations = 2
            else:
                complexity_level = 3
                max_iterations = 3

            logger.info(f"🎯 Complexity: Level {complexity_level}, Capabilities: {len(capabilities)}, Iterations: {max_iterations}")

        except Exception as e:
            logger.warning(f"⚠️ CapabilityAnalyzer failed: {e}, using default complexity")
            capabilities = []
            execution_plan = 'Default execution'
            complexity_level = 1
            max_iterations = 1

        # 🔥 步骤3: 如果是temporal问题,提取时间范围
        time_range = None
        cap_names = [c['name'] for c in capabilities]
        if 'temporal_calculation' in cap_names or 'duration_inference' in cap_names:
            from src.utils.date_extractor import DateExtractor
            time_range = DateExtractor.extract_time_range(user_input)
            if time_range:
                logger.info(f"⏰ Extracted time_range: {time_range}")

        # 步骤4: 记忆检索 (带时间过滤)
        memories = []
        try:
            retrieval_result = await self._activate_agent(
                'memory_retrieval',
                AgentMessage(
                    sender='brain_network_coordinator',
                    receiver='memory_retrieval',
                    message_type='request',
                    content={
                        'action': 'semantic_search',
                        'query': user_input,
                        'k': 20,
                        'time_range': time_range  # 🔥 传递时间范围参数!
                    }
                )
            )

            retrieved_memories = retrieval_result.get('memories', [])
            logger.info(f"🔍 Vector retrieval: {len(retrieved_memories)} memories from FAISS")

            # 分布式分配记忆到脑区
            for mem_data in retrieved_memories:
                if 'memory' in mem_data:
                    content = mem_data['memory'].get('content', '')
                    content_lower = content.lower()

                    regions = []

                    # 情节记忆: 海马体
                    if any(kw in content_lower for kw in ['用户:', '助手:', 'user:', 'assistant:', 'yesterday', 'today', 'on ', 'may', 'attended', 'went to']):
                        regions.append('hippocampus')

                    # 语义记忆: 颞叶
                    if any(kw in content_lower for kw in ['concept', 'knowledge', 'fact', '概念', '知识']):
                        regions.append('temporal')

                    # 情绪记忆: 杏仁核
                    if any(kw in content_lower for kw in ['fear', 'happy', 'sad', 'angry', '害怕', '开心', '难过']):
                        regions.append('amygdala')

                    if not regions:
                        regions = ['hippocampus']  # 默认海马体

                    for region in regions:
                        memories.append({
                            **mem_data,
                            'region': region
                        })

            # 统计分布
            region_counts = {}
            for m in memories:
                region_counts[m['region']] = region_counts.get(m['region'], 0) + 1

            logger.info(f"✅ Distributed to regions: " + ", ".join(f"{r}={c}" for r, c in sorted(region_counts.items())))

        except Exception as e:
            logger.warning(f"Retrieval failed: {e}")

        # 🔥🔥🔥 步骤5: 决策路径

        # 路径A: 如果有特殊推理能力,使用CapabilityOrchestrator
        if len(capabilities) > 0:
            logger.info(f"🎯 Using CapabilityOrchestrator to execute {len(capabilities)} capabilities")

            try:
                from src.reasoning.capability_orchestrator import CapabilityOrchestrator

                agents_dict = {
                    'memory_retrieval': self.memory_retrieval,
                    'reasoning_validator': self.reasoning_validator,
                    'consolidation': self.consolidation,
                    'reflection': self.reflection,
                    'conversation': self.conversation
                }
                orchestrator = CapabilityOrchestrator(brain_agents=agents_dict)

                orchestrator_result = await orchestrator.execute(
                    query=user_input,
                    capabilities=capabilities,
                    memories=memories,
                    execution_plan=execution_plan
                )

                response = orchestrator_result.get('answer') or 'No answer generated'
                confidence = orchestrator_result.get('confidence', 0.7)
                reasoning_chain = orchestrator_result.get('reasoning_chain', [])

                response_preview = response[:100] if len(response) > 100 else response
                logger.info(f"✅ CapabilityOrchestrator completed: {response_preview} (confidence={confidence:.2f})")

                processing_time = (datetime.now() - start_time).total_seconds()
                self.processing_stats['successful_requests'] += 1

                # 存储记忆
                memory_stored = await self._store_memory_if_needed(user_input, response)

                return ProcessingResult(
                    response=response,
                    routing_decision={
                        'mode': 'capability_orchestrator',
                        'complexity_level': complexity_level,
                        'capabilities': [c['name'] for c in capabilities],
                        'execution_plan': execution_plan
                    },
                    agents_involved=orchestrator_result.get('capabilities_used', []),
                    memories_retrieved=memories,
                    memory_stored=memory_stored,
                    processing_time=processing_time,
                    agent_logs={'reasoning_chain': reasoning_chain},
                    insights={
                        'complexity_level': complexity_level,
                        'confidence': confidence,
                        'capabilities_executed': len(capabilities)
                    },
                    success=True
                )
            except Exception as e:
                logger.error(f"❌ CapabilityOrchestrator failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback to BrainNetwork

        # 路径B: 使用BrainNetwork图拓扑激活扩散
        logger.info(f"🧠 Using BrainNetwork: {max_iterations} iterations for Level {complexity_level}")

        network_result = await self.brain_network.process(
            stimulus=user_input,
            context={
                'memories': memories,
                'detected_language': detected_language,
                'complexity': complexity_level
            },
            max_iterations=max_iterations or 5,
            convergence_threshold=0.8
        )

        processing_time = (datetime.now() - start_time).total_seconds()
        self.processing_stats['successful_requests'] += 1

        # 存储记忆
        memory_stored = await self._store_memory_if_needed(user_input, network_result['response'])

        return ProcessingResult(
            response=network_result['response'],
            routing_decision={
                'mode': 'brain_network',
                'converged': network_result['converged'],
                'iterations': network_result.get('convergence_iteration', -1)
            },
            agents_involved=list(network_result.get('workspace', {}).keys()),
            memories_retrieved=memories,
            memory_stored=memory_stored,
            processing_time=processing_time,
            agent_logs=network_result.get('workspace', {}),
            insights={
                'convergence_iteration': network_result.get('convergence_iteration', -1),
                'final_activation': network_result.get('final_activation', {}),
                'confidence': network_result.get('confidence', 0.0),
                'architecture': 'brain_network'
            },
            success=True
        )


    async def _store_memory_if_needed(self, user_input: str, response: str) -> bool:
        """辅助方法: 根据输入类型存储记忆"""
        try:
            is_learning = any(kw in user_input.lower() for kw in [
                'on ', 'may', 'attended', 'researched', 'learned', 'studied'
            ])

            if is_learning:
                memory_id = await self.memory_system.store_memory(
                    content=user_input,
                    importance=0.9,
                    context_tags=['learning', 'event', 'brain_network']
                )
                logger.info(f"📚 Stored learning event: {memory_id}")
                return True
            else:
                conversation_content = f"用户: {user_input}\\n助手: {response}"
                memory_id = await self.memory_system.store_memory(
                    content=conversation_content,
                    importance=0.5,
                    context_tags=['brain_network', 'conversation']
                )
                logger.info(f"💬 Stored conversation: {memory_id}")
                return True
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")
            return False

'''
