#!/bin/bash
# 记忆快照管理脚本
# 用途: 保存/恢复记忆状态,避免测试污染

SNAPSHOT_DIR="data/snapshots"
mkdir -p "$SNAPSHOT_DIR"

case "$1" in
    save)
        # 保存当前记忆为快照
        SNAPSHOT_NAME="${2:-snapshot_$(date +%Y%m%d_%H%M%S)}"
        echo "📸 Saving memory snapshot: $SNAPSHOT_NAME"

        # 复制SQLite数据库
        cp data/brain_memory.db "$SNAPSHOT_DIR/${SNAPSHOT_NAME}.db" 2>/dev/null || \
        cp data/memories.db "$SNAPSHOT_DIR/${SNAPSHOT_NAME}.db" 2>/dev/null || \
        echo "⚠️  No memory database found"

        # 复制FAISS索引 (如果存在)
        if [ -d "data/faiss_index" ]; then
            cp -r data/faiss_index "$SNAPSHOT_DIR/${SNAPSHOT_NAME}_faiss"
        fi

        echo "✅ Snapshot saved: $SNAPSHOT_DIR/$SNAPSHOT_NAME"
        ls -lh "$SNAPSHOT_DIR/${SNAPSHOT_NAME}"*
        ;;

    restore)
        # 恢复快照
        SNAPSHOT_NAME="$2"

        if [ -z "$SNAPSHOT_NAME" ]; then
            echo "Usage: ./snapshot_memory.sh restore <snapshot_name>"
            echo ""
            echo "Available snapshots:"
            ls -1 "$SNAPSHOT_DIR"/*.db 2>/dev/null | sed 's/.*\//  - /' | sed 's/\.db$//'
            exit 1
        fi

        echo "♻️  Restoring memory snapshot: $SNAPSHOT_NAME"

        # 恢复SQLite数据库
        if [ -f "$SNAPSHOT_DIR/${SNAPSHOT_NAME}.db" ]; then
            cp "$SNAPSHOT_DIR/${SNAPSHOT_NAME}.db" data/brain_memory.db
            cp "$SNAPSHOT_DIR/${SNAPSHOT_NAME}.db" data/memories.db 2>/dev/null || true
            echo "  ✅ Database restored"
        else
            echo "  ❌ Snapshot not found: $SNAPSHOT_DIR/${SNAPSHOT_NAME}.db"
            exit 1
        fi

        # 恢复FAISS索引 (如果存在)
        if [ -d "$SNAPSHOT_DIR/${SNAPSHOT_NAME}_faiss" ]; then
            rm -rf data/faiss_index
            cp -r "$SNAPSHOT_DIR/${SNAPSHOT_NAME}_faiss" data/faiss_index
            echo "  ✅ FAISS index restored"
        fi

        echo "✅ Memory restored from: $SNAPSHOT_NAME"
        ;;

    list)
        # 列出所有快照
        echo "Available memory snapshots:"
        echo ""

        for snapshot in "$SNAPSHOT_DIR"/*.db; do
            if [ -f "$snapshot" ]; then
                name=$(basename "$snapshot" .db)
                size=$(ls -lh "$snapshot" | awk '{print $5}')
                date=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$snapshot" 2>/dev/null || \
                       stat -c "%y" "$snapshot" 2>/dev/null | cut -d' ' -f1,2 | cut -d. -f1)
                echo "  📸 $name"
                echo "     Size: $size | Date: $date"

                # 检查FAISS索引
                if [ -d "$SNAPSHOT_DIR/${name}_faiss" ]; then
                    echo "     FAISS: ✅"
                fi
                echo ""
            fi
        done
        ;;

    clean)
        # 删除所有快照
        echo "⚠️  This will delete ALL memory snapshots in $SNAPSHOT_DIR"
        read -p "Continue? (y/N): " confirm

        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -rf "$SNAPSHOT_DIR"/*
            echo "✅ All snapshots deleted"
        else
            echo "Cancelled"
        fi
        ;;

    *)
        echo "Memory Snapshot Manager"
        echo ""
        echo "Usage:"
        echo "  ./snapshot_memory.sh save [name]     - Save current memory as snapshot"
        echo "  ./snapshot_memory.sh restore <name>  - Restore memory from snapshot"
        echo "  ./snapshot_memory.sh list            - List all snapshots"
        echo "  ./snapshot_memory.sh clean           - Delete all snapshots"
        echo ""
        echo "Examples:"
        echo "  ./snapshot_memory.sh save clean_state        # 保存干净状态"
        echo "  ./snapshot_memory.sh restore clean_state     # 恢复干净状态"
        echo "  ./snapshot_memory.sh save after_ingestion    # 保存录入后状态"
        exit 1
        ;;
esac
