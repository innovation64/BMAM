/**
 * BMAM Lightweight i18n Module
 * Bilingual support: English / Chinese
 */
'use strict';

const I18N = (() => {
    const STRINGS = {
        en: {
            'brand': 'BMAM Soul',
            'nav.text': 'Text',
            'nav.voice': 'Voice',
            'nav.monitor': 'Monitor',
            'sidebar.memory': 'Memory Management',
            'sidebar.export': 'Export Brain Package',
            'sidebar.import': 'Import Brain Package',
            'sidebar.search': 'Memory Search',
            'sidebar.search.placeholder': 'Search memories...',
            'sidebar.search.btn': 'Search',
            'sidebar.stats': 'Memory Statistics',
            'sidebar.stats.total': 'Total Memories',
            'sidebar.stats.regions': 'Active Regions',
            'sidebar.lang': 'Language',
            'chat.placeholder': 'Type a message...',
            'chat.send': 'Send',
            'chat.welcome': 'Hello! I am BMAM. Ready to chat.',
            'chat.thinking': 'Thinking...',
            'right.brain': 'Brain Regions',
            'right.reasoning': 'Reasoning Trace',
            'right.memories': 'Retrieved Memories',
            'right.no_reasoning': 'No active reasoning...',
            'right.no_memories': 'No memories retrieved yet.',
            'status.connected': 'Connected',
            'status.disconnected': 'Disconnected',
            'export.loading': 'Exporting...',
            'export.done': 'Exported!',
            'import.loading': 'Importing...',
            'import.done': 'Imported!',
            'time.badge': 'ms',
            'mic.click_to_speak': 'Click to speak',
            'mic.recording': 'Recording... click to stop',
            'mic.init_required': 'Click to enable microphone',
            'toast.mic_connected': 'Microphone connected!',
            'toast.mic_error': 'Microphone error',
            'toast.no_mic_support': 'Your browser does not support microphone access.',
            'toast.mic_denied': 'Microphone permission denied. Please allow it in browser settings.',
            'modal.memory_details': 'Memory Details',
            'modal.close': 'Close',
            'modal.content': 'Content',
            'modal.similarity': 'Similarity',
            'modal.importance': 'Importance',
            'modal.context': 'Context Tags',
            'modal.emotions': 'Emotion Tags',
            'modal.timestamp': 'Timestamp',
            'sidebar.brain_regions': 'Brain Regions',
            'sidebar.reasoning_trace': 'Reasoning Trace',
            'sidebar.memories_title': 'Retrieved Memories',
            'chat.input_placeholder': 'Type a message...',
        },
        zh: {
            'brand': 'BMAM',
            'nav.text': '文字',
            'nav.voice': '语音',
            'nav.monitor': '监控',
            'sidebar.memory': '记忆管理',
            'sidebar.export': '导出记忆包',
            'sidebar.import': '导入记忆包',
            'sidebar.search': '记忆搜索',
            'sidebar.search.placeholder': '搜索记忆...',
            'sidebar.search.btn': '搜索',
            'sidebar.stats': '记忆统计',
            'sidebar.stats.total': '总记忆数',
            'sidebar.stats.regions': '活跃脑区',
            'sidebar.lang': '语言',
            'chat.placeholder': '输入消息...',
            'chat.send': '发送',
            'chat.welcome': '你好！我是 BMAM，准备好聊天了。',
            'chat.thinking': '思考中...',
            'right.brain': '脑区活动',
            'right.reasoning': '推理轨迹',
            'right.memories': '检索到的记忆',
            'right.no_reasoning': '暂无推理活动...',
            'right.no_memories': '暂无检索到的记忆。',
            'status.connected': '已连接',
            'status.disconnected': '未连接',
            'export.loading': '导出中...',
            'export.done': '已导出！',
            'import.loading': '导入中...',
            'import.done': '已导入！',
            'time.badge': '毫秒',
            'mic.click_to_speak': '点击说话',
            'mic.recording': '录音中…点击停止',
            'mic.init_required': '点击启用麦克风',
            'toast.mic_connected': '麦克风已连接！',
            'toast.mic_error': '麦克风错误',
            'toast.no_mic_support': '您的浏览器不支持麦克风访问。',
            'toast.mic_denied': '麦克风权限被拒绝，请在浏览器设置中允许。',
            'modal.memory_details': '记忆详情',
            'modal.close': '关闭',
            'modal.content': '内容',
            'modal.similarity': '相似度',
            'modal.importance': '重要性',
            'modal.context': '上下文标签',
            'modal.emotions': '情感标签',
            'modal.timestamp': '时间',
            'sidebar.brain_regions': '脑区活动',
            'sidebar.reasoning_trace': '推理轨迹',
            'sidebar.memories_title': '检索到的记忆',
            'chat.input_placeholder': '输入消息...',
        }
    };

    let currentLang = localStorage.getItem('bmam_lang') || 'en';

    function t(key) {
        return (STRINGS[currentLang] && STRINGS[currentLang][key])
            || (STRINGS['en'] && STRINGS['en'][key])
            || key;
    }

    function getLang() {
        return currentLang;
    }

    function setLang(lang) {
        if (STRINGS[lang]) {
            currentLang = lang;
            localStorage.setItem('bmam_lang', lang);
            applyAll();
        }
    }

    function toggle() {
        setLang(currentLang === 'en' ? 'zh' : 'en');
    }

    function applyAll() {
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const target = el.getAttribute('data-i18n-attr');
            if (target === 'placeholder') {
                el.placeholder = t(key);
            } else {
                el.textContent = t(key);
            }
        });
    }

    return { t, getLang, setLang, toggle, applyAll };
})();
