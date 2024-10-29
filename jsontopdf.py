import json

# JSON 파일 읽기
with open('/Users/apple/Downloads/KB TEST 826/ragdata.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

# 새로운 형식으로 변환
formatted_data = []
for i, item in enumerate(data, 1):
    formatted_line = f"no.{i} human: {item['input']}, AI: {item['output']}"
    formatted_data.append(formatted_line)

# 결과를 텍스트 파일로 저장
with open('formatted_data.txt', 'w', encoding='utf-8') as file:
    file.write('\n'.join(formatted_data))

print("변환이 완료되었습니다. 'formatted_data.txt' 파일을 확인해주세요.")