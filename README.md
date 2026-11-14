# Shopping Agent

Shopping Skill สำหรับ Codex พร้อมเครื่องคำนวณการเงินในเครื่อง เป้าหมายการออม และตัวอย่างแชท Shopping สีขาว–ดำ ไม่ใช้ API แบบเสียเงินและไม่ส่งข้อมูลการเงินออกไปค้นสินค้า

## ใช้กับ Codex

Clone repository นี้แล้วเปิดโฟลเดอร์ใน Codex จากนั้นเรียก:

```text
$shopping-agent
$shopping-agent ช่วยเปรียบเทียบรองเท้ารุ่นที่ฉันสนใจ
$shopping-agent อยากเก็บเงินซื้อของ ต้องเริ่มยังไง
```

Skill อยู่ที่ [`.agents/skills/shopping-agent/SKILL.md`](.agents/skills/shopping-agent/SKILL.md) หากต้องการติดตั้งในพื้นที่ skills ของผู้ใช้ ให้คัดลอกโฟลเดอร์ `shopping-agent` ภายใน `.agents/skills/` ไปยังโฟลเดอร์ skills ที่ Codex ของคุณใช้งาน แล้วเริ่ม session ใหม่

ชื่อ/รูป/URL สินค้าใช้ระบุสินค้าและหาหลักฐานผ่านเครื่องมือของ Codex ที่มีอยู่ การค้นหาร้านค้าไม่ได้ทำโดย Python engine และไม่มี API key รวมอยู่ใน repo ความสามารถ inline UI ขึ้นอยู่กับ host; มี Markdown/Native Selection เป็นทางเลือก

## สิ่งที่ทำได้

- ระบุสินค้าและยืนยันรุ่น แยก identification confidence กับ listing-match confidence
- เทียบราคาจากหลักฐาน รวมค่าส่งที่ยืนยันและส่วนลดที่มีสิทธิ์จริง
- Financial Fit, ระยะเวลาเก็บเงิน และเปรียบเทียบผลกระทบด้วย Python
- เป้าหมายหลายประเภท การจัดสรรงบร่วมกัน ปฏิทิน และการป้องกันบันทึกซ้ำ
- งบรายวัน Money Leak และวางงบทริปด้วยเครื่องคำนวณชุดเดียวกัน
- ตัวอย่าง Dashboard บนเครื่อง พร้อมแชทขาว–ดำที่รับชื่อสินค้า ราคา และค่าส่งต่อเนื่องกันได้

## เปิด Dashboard ตัวอย่าง

ใช้ Python 3.10 ขึ้นไป ไม่ต้องติดตั้งแพ็กเกจสำหรับฟังก์ชันหลัก

Windows: ดับเบิลคลิก `start-dashboard.bat` หรือรันจากโฟลเดอร์ repo:

```sh
python dashboard/server.py --open
```

เปิด `http://127.0.0.1:8877` หยุดด้วย Ctrl+C หากพอร์ตถูกใช้ ให้เพิ่ม `--port 8878`

Dashboard เป็น **Demo Mode เท่านั้น** ใช้ข้อมูลจำลองจาก fixtures และเก็บเป้าหมายแยกใน `local/dashboard-demo.sqlite3` แชทเป็น local rule router ไม่ใช่ AI สนทนาอิสระ ยังไม่ค้นหาราคาสดหรืออ่านรูปเอง ใช้ Codex Chat สำหรับการค้นหาจริง การพิมพ์ข้อความและเลื่อน Slider ไม่ซื้อสินค้า ไม่โอนเงิน และไม่บันทึกธุรกรรม

## เชื่อมข้อมูลการเงินจริง

ยังไม่มี provider ถูกเลือกโดยปริยาย ให้ระบุโฟลเดอร์ provider ภายในเครื่องที่ผู้ใช้อนุญาตด้วย `--finance-dir` เท่านั้น อ่าน AGENTS.md และตรวจ schema จริงก่อนใช้ตาม [data contract](.agents/skills/shopping-agent/references/data-contract.md) และ [planning contract](.agents/skills/shopping-agent/references/planning-contract.md)

ไม่มี ledger สลิป profile จริง หรือ API key อยู่ใน repo ห้ามเพิ่มข้อมูลเหล่านี้ใน commit ค่าไม่ทราบ/ศูนย์ที่ยังไม่ยืนยันไม่ถือว่าเป็นศูนย์ และข้อมูลธุรกรรมไม่ใช่ยอดบัญชีปัจจุบัน

CLI รับ payload ผ่าน stdin หรือไฟล์ local ที่ gitignore ไว้ ไม่ใส่ข้อมูลส่วนตัวใน arguments ดู workflow ใน Skill และ references ที่เกี่ยวข้อง การสร้างหรือเปลี่ยนเป้าหมายต้องยืนยันก่อนเสมอ หากติดตั้ง skill แบบใช้ร่วมหลายโปรเจกต์ ให้ระบุ `--store <workspace>/local/goals.sqlite3` หรือกำหนด `SHOPPING_WORKSPACE` เพื่อแยกข้อมูล

## ทดสอบ

```sh
python -m unittest discover -s .agents/skills/shopping-agent/tests -p "test_*.py"
python -m unittest discover -s dashboard -p "test_*.py"
python .agents/skills/shopping-agent/scripts/test_comparison_states.py
```

มี Node.js จึงรันการทดสอบ UI แบบ DOM จำลองเพิ่มได้:

```sh
node --test .agents/skills/shopping-agent/component_tests/test_companion_dom.cjs .agents/skills/shopping-agent/component_tests/test_goal_dom.cjs .agents/skills/shopping-agent/component_tests/test_purchase_dom.cjs
python .agents/skills/shopping-agent/scripts/test_simulator_view.py --node node
```

การทดสอบ PNG เป็นตัวเลือกแยก ต้องมี Pillow และฟอนต์ไทยที่ renderer รองรับ ฟังก์ชันการเงินหลักไม่ import Pillow ชุดทดสอบใช้ข้อมูลจำลอง/ฐานข้อมูลชั่วคราว การทดสอบ DOM ไม่ใช่หลักฐานว่าปุ่ม inline ทำงานใน Codex ทุกเวอร์ชัน
