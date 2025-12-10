#!/bin/bash

# 生成UUID的函数
generate_uuid() {
    python3 -c "import uuid; print(uuid.uuid4())"
}

# 创建测试数据
UUID1=$(generate_uuid)
UUID2=$(generate_uuid)

echo "测试UUID1: $UUID1"
echo "测试UUID2: $UUID2"

# 测试批量生成
curl -X POST http://localhost:8000/api/slide/batch/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"slides\": [
      {
        \"id\": \"$UUID1\",
        \"page_num\": 1,
        \"type\": \"cover\",
        \"title\": \"测试封面\",
        \"content_text\": \"这是一个测试封面\",
        \"visual_desc\": \"简洁现代的封面设计，蓝色背景\"
      },
      {
        \"id\": \"$UUID2\",
        \"page_num\": 2,
        \"type\": \"content\",
        \"title\": \"内容页\",
        \"content_text\": \"这是测试内容\",
        \"visual_desc\": \"清晰的内容布局，白色背景\"
      }
    ],
    \"style_prompt\": \"现代简约风格，蓝色主题，专业商务\",
    \"max_workers\": 2,
    \"aspect_ratio\": \"16:9\"
  }"