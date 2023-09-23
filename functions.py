import variables as var

"""
$, $$, $<const>, (<n1> <+ | -> <n2>...),
0x<hex>, <decimal>, 0b<bin>, ?, &<name>, '<char>'
Code from LASM v0.0.1-superbeta:
process(v, s, n)	-> zeroExtend(toHex(v, s), s, n)
memProc(v, s)		-> reverse(splitBytes(process(v, s, False)))
"""


def overflowError(size: int, expected: int, index: int) -> None:
	var.raiseError(
		"Overflow Error",
		f"Used size({var.str_size[size]}) is smaller than should({var.str_size[expected]}) be used.",
		line=index,
	)


def findSize(x: int, algin: bool = True, forge_sign: bool = False) -> int:
	if not x:
		return var.BYTE

	if x < 0:
		x = (-x << 1) - 1
	elif forge_sign:
		x <<= 1

	if x > 0xFFFF_FFFF:
		var.raiseError(
			"Overflow Error",
			"This Assembler cant handle bigger numbers than 32 bit.",
		)
		return var.DWORD

	tmp = 0
	while x:
		x >>= 8
		tmp += 2
	return var.DWORD if (tmp == 6 and algin) else tmp


def split_without_specs(x: str) -> list[str]:
	retu: list[str] = []
	tmp = ""
	include = True
	for char in x:
		if char in '"()':
			include = not include
			tmp += char
		elif char == " " and include:
			if tmp != "":
				retu.append(tmp)
				tmp = ""
		elif char != "_":
			tmp += char
	retu.append(tmp)
	return retu


def get_register(x: str, mod: bool = True) -> tuple[int, int]:
	if x in var.seg_register:
		return (var.seg_register.index(x), -1)

	tmp = var.str_register.index(x[-2:])
	return (
		tmp % var.REG_INDEX_LEN if mod else tmp,
		var.DWORD
		if len(x) == 3
		else (var.BYTE if tmp < var.REG_INDEX_LEN else var.WORD),
	)


if __name__ == "__main__":
	from typing import Any

	expected = [
		var.BYTE,
		var.WORD,
		var.DWORD,
		6,
		var.DWORD,
		var.BYTE,
		"0430",
		"12",
		"fe",
		["34", "56"],
		["a3", "45", "6"],
		6,
		0x10,
		0,
		["test"],
		[True],
		512,
		["32", "04"],
		(0, var.DWORD),
		(3, -1),
	]
	len_ = len(expected)

	var.orgin = 0x10
	var.addr = 0x20

	retu: list[Any] = [
		findSize(255),
		findSize(0xFFFF),
		findSize(0xFFFFFF),
		findSize(0xFFFFFF, False),
		findSize(0xFFFFFFFF, False),
		findSize(-128),
		var.zero_extend("430", var.WORD),
		var.zero_extend("430012"),
		var.to_hex(-2),
		var.split_bytes("3456"),
		var.split_bytes("a3456"),
		var.compute_int("(3+5-2)"),
		var.compute_int("(0x20-$+$$)"),
		var.to_sign_int("-&test"),
		var.event.name_list,
		var.event.sign_list,
		var.to_int("^9"),
		var.memory_proc(0x432, var.WORD),
		get_register("eax"),
		get_register("ds"),
	]

	for i in range(len_):
		print(f"{i}:\t", retu[i])
		assert retu[i] == expected[i]
	del expected, retu
	print(f"All tests succesfully passed! ({len_}/{len_})")

	var.raiseError("Test Error", "Hello, world! (This is an test error.)")
	try:
		print(var.calculate_int("- $"))
		var.raiseError(
			"Space Support",
			"Math calculations support 'space' character in calculations.",
			False,
		)
	except:
		var.raiseError(
			"Space Support",
			"Math calculations dont support 'space' character in calculations, in another terms to_int(x) function dont strip(remove spaces from sides.) input value 'x'.",
			False,
		)
