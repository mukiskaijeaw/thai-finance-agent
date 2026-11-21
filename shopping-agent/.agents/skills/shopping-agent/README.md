# Shopping Agent สำหรับ Codex Chat

Pillar 4 แบบ skill + Python CLI ต่อยอด engine เดิม ไม่มี HTML, frontend, dashboard, web server หรือ API key ใหม่

## เรียกใช้งาน

หลังติดตั้ง พิมพ์ใน Codex:

```text
$shopping-agent ช่วยหารองเท้าวิ่งสีดำและเปรียบเทียบราคาในไทย
$shopping-agent ระบุรุ่นสินค้าจากรูปนี้
$shopping-agent ตัวเลือกนี้ซื้อไหวไหม และต้องเก็บอีกกี่เดือน
```

แนบรูปผ่านแชทได้โดยตรง ไม่ต้องเปิดเว็บแอป ไม่ต้องให้ผู้ใช้กรอก JSON Agent จัดหลักฐานและเรียก helper ให้เอง

โหมดสาธิต: ขอในแชทว่า “ลองใช้ข้อมูลจำลองประเมินให้ดู” หรือเรียก `python scripts/shopping.py demo --format markdown` ข้อมูลการเงินและรายการสินค้าทั้งหมดเป็น synthetic จาก references/demo.json ไม่ใช้หรือแก้ CSV จริง ไม่มีการเติม mock ให้การประเมินจริงโดยปริยาย ผลจำลองไม่ใช่คำแนะนำตามสถานะการเงินของผู้ใช้

เมื่อต้องการตัดสินใจซื้อ ผลการเงินแสดงเป็น Markdown Summary Card: สถานะ, ราคาสุทธิตัวเด่น, metric table, ระยะเวลาเก็บเงิน, แถบความคืบหน้า 10 ช่อง, คำแนะนำ และข้อจำกัด แถบคำนวณใน engine จากเงินในแผนเก็บซื้อ ไม่ใช้ budget แทนเงินสด ข้อมูลขาดแสดงยังประเมินไม่ได้ ไม่มีเปอร์เซ็นต์สมมติ การถามแค่ราคายังแสดงตารางสินค้าเดิม

Skill หลักอยู่ใน `shopping-agent/.agents/skills/shopping-agent` แยกจาก Pillar 1 และเชื่อมไป user skills เพื่อเรียกข้ามโปรเจกต์ได้ วิธีค้นพบ local skill อ้างอิง [OpenAI Docs](https://learn.chatgpt.com/docs/build-skills) หากยังไม่ปรากฏให้เริ่ม Codex ใหม่ หรือสั่งให้อ่าน SKILL.md ของแพ็กเกจโดยตรง

ไม่มี financial source เชื่อมโดยปริยาย ใช้ `--finance-dir` หรือ `FINANCE_DIR` เพื่อเลือก local provider เมื่อประเมินการเงินเท่านั้น ตัวอย่าง `--finance-dir ../thai-finance-agent` (เมื่อรันจาก shopping-agent) การค้นสินค้าไม่อ่าน provider แม้ตั้งค่าไว้ ไม่มีการย้าย/คัดลอกฐานข้อมูลการเงินมาไว้ใน Pillar 4

เสนอสินค้าพร้อมภาพจริงเมื่อยืนยันตรงรุ่น/สีได้ โดยส่ง image_url/image_source และ flags ยืนยันสองตัวเข้า helper รูปที่ไม่ยืนยันหรือไม่มีแหล่งที่มาจะไม่ถูก embed ดูรายละเอียดผู้ใช้ใหม่ใน references/onboarding.md

## โครงสร้างและ data flow

- SKILL.md: intent routing, ค้นเว็บ/ดูรูปใน Codex, output แชท, privacy
- scripts/engine.py: Decimal, evidence confidence, Financial Fit, savings time, comparison; นำกลับมาใช้จาก engine เดิมและแก้ edge cases
- scripts/shopping.py: CLI stdin JSON → engine → JSON/Markdown, local financial adapter และ watchlist ที่ต้อง consent
- references/data-contract.md: schema และนิยามตัวแปร/สมมติฐาน
- tests/: regression ของเครื่องคำนวณเดิมและ Chat CLI integration ใหม่
- shopping_test_cases.md: acceptance cases สำหรับ chat

คำขอสินค้า → Codex ระบุ intent/หลักฐาน → web tools เฉพาะคุณลักษณะสินค้า → ราคาที่ตรวจ → local engine → Markdown ในแชท

คำขอการเงิน → อ่าน AGENTS.md และ database.csv ใน Pillar 1 ล่าสุด → observed totals และ data-quality → รวมข้อมูลที่ผู้ใช้ยืนยันเมื่อขาด → local engine → สรุปเฉพาะที่จำเป็น ไม่ส่ง ledger/profile ไป search/retailer

ไม่มี profile ที่ยืนยันปัจจุบันใน Pillar 1 จึงไม่สมมติเงินสด หนี้ หรือเงินสำรองจากรายการธุรกรรม Legacy profile ใน smartbuy-deploy ไม่ถูกใช้โดยอัตโนมัติ

## รันทดสอบ

Python 3.10+ standard library:

```text
python -m unittest discover -s tests -v
```

CLI สำหรับ agent/developer (ผู้ใช้ทั่วไปใช้แชท):

```text
python scripts/shopping.py ledger --finance-dir <Pillar1-directory>
python scripts/shopping.py evaluate --format markdown
python scripts/shopping.py query
```

evaluate/query อ่าน JSON จาก stdin เมื่อไม่มี --input; อย่าใส่ข้อมูลการเงินใน command arguments ห้าม commit ข้อมูลจริงหรือสร้าง demo จากธุรกรรมจริง ไม่มีการสร้าง profile หรือบันทึก watchlist จริงในขั้นตอนติดตั้ง

## ข้อจำกัด

ตัว CLI ไม่ค้นเว็บหรือวิเคราะห์รูปเอง แต่ Codex เป็นผู้ใช้เครื่องมือเหล่านั้นและส่งหลักฐานให้ engine ระดับ confidence คือความครบถ้วนของหลักฐาน ไม่ใช่โอกาสถูกและไม่ตรวจ source อัตโนมัติ ภาระอนาคตกันทั้งยอดล่วงหน้า ไม่จำลอง due dates รายวัน ไม่มี monitoring/scheduler ไม่มีการสั่งซื้อ

การใช้ Codex Chat ยังคงเป็นการใช้งานตามการตั้งค่าบัญชี/เครื่องมือของ Codex คำว่า local ในที่นี้หมายถึงไฟล์และการคำนวณ Python ในเครื่อง ไม่มีการรับประกันว่าแชททั้งหมดทำงาน offline ไม่ส่งข้อมูลไปยังร้านค้าหรือบริการค้นหาภายนอก
