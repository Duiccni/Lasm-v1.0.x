from typing import Any


class settings:
	tab_size = 22
	exit_on_errors = False
	skip_print = False
	skip_times = False
	show_times = True
	print_error = True
	linewrite_msg = False
	debug = True

	@staticmethod
	def mode(*args: Any) -> None:
		settings.tab_size = args[0]
		settings.exit_on_errors = args[1]
		settings.skip_print = args[2]
		settings.skip_times = args[3]
		settings.show_times = args[4]
		settings.print_error = args[5]
		settings.debug = args[6]


class colors:
	ENDL = "\033[0m"
	ITALIC = "\033[3m"
	DARK = "\033[90m"
	WARNING = "\033[32m"
	ERROR = "\033[31m"
	SECOND = "\033[34m"
	PINK = "\033[35m"
	GREEN = "\033[93m"


memory: list[str] = []
constants: dict[str, int] = {}
addr = 0
orgin = 0

# BIT_32 = 0x66
STR_BIT_32 = "66"

BYTE = 2
WORD = 4
DWORD = 8

sizes = {
	"byte": BYTE,
	"word": WORD,
	"dword": DWORD,
	"x8": BYTE,
	"x16": WORD,
	"x32": DWORD,
	"short": BYTE,
	"near": WORD,
	"long": DWORD,
	"far": DWORD,
}

str_size = {
	BYTE: "byte",
	WORD: "word",
	DWORD: "dword",
}


def replace_memory(start: int, values: list[str]) -> None:
	for i in range(len(values)):
		memory[start + i] = values[i]


class event:
	message_event: list[int] = []
	name_list: list[str] = []
	sign_list: list[bool] = []
	_added = False

	@staticmethod
	def name_add(x: str) -> None:
		event.name_list.append(x)
		event._added = True

	@staticmethod
	def sign_add(x: bool) -> None:
		if event._added:
			event.sign_list.append(x)
			event._added = False

	@staticmethod
	def clear() -> None:
		event.name_list.clear()
		event.sign_list.clear()


def raiseError(title: str, msg: str, error: bool = True, line: int | None = None):
	if settings.print_error:
		print(
			colors.WARNING + title + ":",
			(colors.ERROR if error else colors.SECOND) + msg + colors.ENDL,
			f"{colors.ITALIC}(Line {line if line != None else '?'}.){colors.ENDL}",
		)
	if error and settings.exit_on_errors:
		exit()


def to_int(x: str) -> int:
	if x == "$":
		return addr
	if x == "$$":
		return orgin
	if x[0] == "&":
		x = x[1:]
		if x in constants:
			return constants[x]
		event.name_add(x)
		return 0
	if x[0] == "'" and x[2] == "'" and len(x) == 3:
		return ord(x[1])
	if x[0] == "^":
		return 1 << to_int(x[1:])
	return int(x, 0)


def to_sign_int(x: str) -> int:
	sign = x[0] == "-"
	value = to_int(x[1:] if sign or x[0] == "+" else x)
	event.sign_add(sign)
	return -value if sign else value


def calculate_int(x: str) -> int:
	tmp = ""
	retu = 0
	sign = x[0] == "-"
	if sign or x[0] == "+":
		x = x[1:]
	for char in x:
		sign_tmp = char == "-"
		if sign_tmp or char == "+":
			retu += -to_int(tmp) if sign else to_int(tmp)
			event.sign_add(sign)
			tmp = ""
			sign = sign_tmp
		else:
			tmp += char
	retu += -to_int(tmp) if sign else to_int(tmp)
	event.sign_add(sign)
	return retu


def compute_int(x: str) -> int:
	if x[0] == "(" and x[-1] == ")":
		return calculate_int(x[1:-1])
	return to_sign_int(x)


def to_hex(x: int, size: int = BYTE) -> str:
	tmp = 1 << (size << 2)  # BYTE = 0xFF, WORD = 0xFFFF
	if x > tmp:
		raiseError(
			"Overflow Error",
			f"to_hex function found an input 'x'({x}) thats bigger than input size({tmp}).",
		)
	return hex(x % tmp)[2:]


def zero_extend(x: str, size: int = BYTE) -> str:
	tmp = size - len(x)
	if tmp < 0:
		raiseError(
			"Overflow Error",
			"zero_extend function found an Negative value, so return value is Shrink of input.",
			False,
		)
		return x[-tmp:]
	return "0" * tmp + x


def split_bytes(x: str) -> list[str]:
	if len(x) % 2 != 0:
		raiseError(
			"Warning",
			f"split_bytes did get an string({x}) with odd number of chars.",
			False,
		)
	return [x[i : i + BYTE] for i in range(0, len(x), BYTE)]


def memory_proc(x: int, size: int) -> list[str]:
	tmp = [i for i in split_bytes(zero_extend(to_hex(x, size), size))]
	tmp.reverse()
	return tmp


class waiter:  # Auto
	def __init__(self, start: int, bias: int, index: int, size: int) -> None:
		self.NAMES = event.name_list.copy()
		self.names = self.NAMES.copy()
		self.signs = event.sign_list.copy()
		event.clear()
		self.bias = bias
		self.start = start
		self.index = index
		self.size = size

	def check(self, name: str) -> bool:
		if name in self.names:
			self.names.remove(name)
		if self.names:
			return False
		replace_memory(
			self.start,
			memory_proc(
				self.bias
				+ sum(
					[
						-constants[self.NAMES[i]]
						if self.signs[i]
						else constants[self.NAMES[i]]
						for i in range(len(self.NAMES))
					]
				),
				self.size,
			),
		)
		return True


waiters: list[waiter] = []

register_8 = ["al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"]
register_16_32 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
seg_register = ["es", "cs", "ss", "ds", "fs", "gs"]

str_register = register_8 + register_16_32

# REGS_LEN = 16
REG_INDEX_LEN = 8

no_input_inst = {
	"nop": ["90"],
	"hlt": ["f4"],
	"cmc": ["f5"],
	"clc": ["f8"],
	"stc": ["f9"],
	"cli": ["fa"],
	"sti": ["fb"],
	"cld": ["fc"],
	"std": ["fd"],
	"pusha": ["60"],
	"popa": ["61"],
	"pushad": [STR_BIT_32, "60"],
	"popad": [STR_BIT_32, "61"],
	"ret": ["c3"],
	"sret": ["c3"],
	"fret": ["cb"],
	"int3": ["cc"],
	"int0": ["ce"],
	"int1": ["f1"],
	"syscall": ["0f", "05"],
	"stosb": ["aa"],
	"stosw": ["ab"],
	"stosd": [STR_BIT_32, "ab"],
	"lodsb": ["ac"],
	"lodsw": ["ad"],
	"lodsd": [STR_BIT_32, "ad"],
}

# mbr: 0x55AA
# borg: 0x7C00
# hkb: 0x200

# Jump if condition (.short)
jcc_inst = {
	"jo": 0x70,
	"jno": 0x71,
	"jb": 0x72,
	"jc": 0x72,
	"jnae": 0x72,
	"jnb": 0x73,
	"jnc": 0x73,
	"jae": 0x73,
	"je": 0x74,
	"jz": 0x74,
	"jne": 0x75,
	"jnz": 0x75,
	"jbe": 0x76,
	"jna": 0x76,
	"ja": 0x77,
	"jnbe": 0x77,
	"js": 0x78,
	"jns": 0x79,
	"jpe": 0x7A,
	"jp": 0x7A,
	"jpo": 0x7B,
	"jnp": 0x7B,
	"jnge": 0x7C,
	"jl": 0x7C,
	"jge": 0x7D,
	"jnl": 0x7D,
	"jle": 0x7E,
	"jng": 0x7E,
	"jnle": 0x7F,
	"jg": 0x7F,
	"jcxz": 0xE3,
}

shift_inst: dict[str, tuple[int, str]] = {
	"shl": (0xE0, "26"),
}
shift_names = ["rol", "ror", "rcl", "rcr", "sal", "shr", "sar"]

for i in range(len(shift_names)):
	byte_x = i << 3
	shift_inst[shift_names[i]] = (
		0xC0 + byte_x,
		zero_extend(hex(0x06 + byte_x)[2:]),
	)

del shift_names

type1_inst = {
	"inc": (0xC0, 0xFE, "0e"),
	"dec": (0xC8, 0xFE, "0e"),
	"not": (0xD0, 0xF6, "16"),
	"neg": (0xD8, 0xF6, "16"),
}

type2_inst = {
	"push": (0x50, "ff", "36"),
	"pop": (0x58, "8f", "06"),
}

type4_inst = {
	"mul": (0xE0, "26"),
	"div": (0xF0, "36"),
}

# (0x04 + 8x, 0xC0 + 8x, 8x, str(0x06 + 8x))
type3_inst: dict[str, tuple[int, int, int, str]] = {}
type3_names = ["add", "or", "adc", "sbb", "and", "sub", "xor", "cmp"]

for i in range(len(type3_names)):
	byte_x = i << 3
	type3_inst[type3_names[i]] = (
		0x04 + byte_x,
		0xC0 + byte_x,
		byte_x,
		zero_extend(hex(0x06 + byte_x)[2:]),
	)

del type3_names

push_segment_values = [
	["06"],
	["0e"],
	["16"],
	["1e"],
	["0f", "a0"],
	["0f", "a8"],
]

pop_segment_values = [
	["07"],
	None,
	["17"],
	["1f"],
	["0f", "a1"],
	["0f", "a9"],
]


def _split_list(list_: list[str], sep: str = "---") -> list[list[str]]:
	retu: list[list[str]] = []
	tmp: list[str] = []
	for i in list_:
		i = i.strip()
		if i == sep:
			retu.append(tmp.copy())
			tmp.clear()
		else:
			tmp.append(i)
	retu.append(tmp)
	del tmp
	return retu

'''
_test_cases_file = open("test_cases.txt")
test_cases = _split_list(_test_cases_file.readlines())
_test_cases_file.close()
'''
test_cases = [["nop"]]

if __name__ == "__main__":
	print(colors.DARK, colors.ITALIC, "abc", colors.DARK, "abc", colors.ENDL, "abc")
	zero_extend("e")

	input()
	memory = [zero_extend(hex(i)[2:]) for i in range(16)]
	event.name_add("a1")
	event.sign_add(False)
	event.name_add("b1")
	event.sign_add(False)
	obj_waiter = waiter(2, 0x200, 0xF0, WORD)

	constants["a1"] = 6
	print(obj_waiter.check("a1"))
	print(obj_waiter.names)
	constants["b1"] = 3
	print(obj_waiter.check("b1"))
	print(obj_waiter.names)

	print(" ".join(memory))

	input()
	print("\n\n".join(["\n".join(i) for i in test_cases]))

	input()
	for i in range(100):
		print(f"\033[{i}m{i} abd{colors.ENDL}")
