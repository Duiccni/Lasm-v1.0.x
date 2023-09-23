import variables as var
import functions as func
from typing import Any, Callable

index_ = 0


def get_memory_addr() -> int:
	return var.addr - var.orgin


def C_int(split_: list[str]) -> list[str]:
	return ["cd", var.zero_extend(hex(var.to_int(split_[0]))[2:])]


# If size didn't given size equals BYTE.
def C_def(split_: list[str]) -> list[str]:
	c_size = var.sizes[split_.pop(0)[1:]] if split_[0][0] == "." else var.BYTE
	retu: list[str] = []
	for num in split_:
		num = num.rstrip(",")
		if num[0] == '"' and num[-1] == '"':
			retu += [var.zero_extend(hex(ord(char))[2:]) for char in num[1:-1]]
		else:
			value = var.compute_int(num)
			tmp = func.findSize(value)
			if tmp > c_size:
				func.overflowError(c_size, tmp, index_)
			if var.event.name_list:
				var.waiters.append(
					var.waiter(
						var.addr - var.orgin,
						value,
						index_,
						c_size,
					)
				)
				return ["XX"] * (c_size >> 1)
			retu += var.memory_proc(value, c_size)
	return retu


# If size didn't given size equals WORD.
def _jmp_call_main(split_: list[str], type: bool) -> list[str] | None:
	if split_[0][0].isalpha():
		index, size = func.get_register(split_[0])
		return ([var.STR_BIT_32] if size == var.DWORD else []) + [
			"ff",
			hex((0xD0 if type else 0xE0) + index)[2:],
		]
	value, size = (
		(split_[1], var.sizes[split_[0][1:]])
		if split_[0][0] == "."
		else (split_[0], var.WORD)
	)
	if value == "$":
		if type:
			var.raiseError("Command", "Calling the same position?", False, index_)
			return
		return ["eb", "fe"]

	# *** compute values ***
	cmd_size = 1 + (size == var.DWORD)  # len(eb)
	# XX - len(eb XX) - $
	number = var.compute_int(value) - cmd_size - (size >> 1) - var.addr

	# *** check waiter ***
	if var.event.name_list:
		var.waiters.append(
			var.waiter(
				var.addr - var.orgin + cmd_size,
				number,
				index_,
				size,
			)
		)
		memory_value = ["XX"] * (size >> 1)
	else:
		memory_value = var.memory_proc(number, size)

	# *** check error ***
	tmp = func.findSize(number, forge_sign=True)
	if size < tmp:
		func.overflowError(size, tmp, index_)

	# *** return ***
	return (
		([var.STR_BIT_32] if size == var.DWORD else [])
		+ [("e8" if type else ("eb" if size == var.BYTE else "e9"))]
		+ memory_value
	)


def C_jmp(split_: list[str]) -> list[str] | None:
	return _jmp_call_main(split_, False)


def C_call(split_: list[str]) -> list[str] | None:
	return _jmp_call_main(split_, True)


def _glob1c_sub(size: int, bias: int):
	return ([var.STR_BIT_32] if size == var.DWORD else []) + [
		var.zero_extend(hex(bias + (size != var.BYTE))[2:])
	]


# If size didn't given size equals WORD.
def _glob1c_main(split_: list[str], args: tuple[int, int, str]) -> list[str]:
	if split_[0][0].isalpha():
		index, size = func.get_register(split_[0])
		return _glob1c_sub(size, args[1]) + [hex(args[0] + index)[2:]]
	value, size = (
		(split_[1], var.sizes[split_[0][1:]])
		if split_[0][0] == "."
		else (split_[0], var.WORD)
	)

	# value's first char is cropped cuz its pointer "*0x4321"
	number = var.compute_int(value[1:])

	if var.event.name_list:
		var.waiters.append(
			var.waiter(
				var.addr - var.orgin + 2 + (size == var.DWORD),
				number,
				index_,
				var.WORD,
			)
		)
		memory_value = ["XX", "XX"]  # WORD size
	else:
		memory_value = var.memory_proc(number, var.WORD)

	return _glob1c_sub(size, args[1]) + [args[2]] + memory_value


def C_not(split_: list[str]) -> list[str]:
	return _glob1c_main(split_, var.type1_inst["not"])


def C_neg(split_: list[str]) -> list[str]:
	return _glob1c_main(split_, var.type1_inst["neg"])


def _inc_dec_main(split_: list[str], bias: int) -> list[str]:
	if split_[0][0].isalpha() and split_[0][1] not in "lh":
		index, size = func.get_register(split_[0])
		return ([var.STR_BIT_32] if size == var.DWORD else []) + [hex(bias + index)[2:]]
	return _glob1c_main(split_, var.type1_inst["inc" if bias == 0x40 else "dec"])


def C_inc(split_: list[str]) -> list[str]:
	return _inc_dec_main(split_, 0x40)


def C_dec(split_: list[str]) -> list[str]:
	return _inc_dec_main(split_, 0x48)


# *** 'mov' command :D ***
_CONST = 0
_PTR = 1
_REG = 2


def _convert_it(x: str, mod_reg: bool = True) -> tuple[Any, int]:
	if x[0].isalpha():
		return func.get_register(x, mod_reg), _REG
	type = _PTR if x[0] == "*" else _CONST
	value = var.compute_int(x[1:] if type == _PTR else x)
	if var.event.name_list:
		var.event.message_event.append(type)
		var.waiters.append(
			var.waiter(
				0,
				value,
				index_,
				type,
			)
		)
	return value, type


def _mov_sub(reg: int, val: int, size: int, bias: int, _ps: int = 0) -> list[str]:
	if var.event.message_event:
		tmp2 = ["XX", "XX"]
		var.waiters[-1].size = var.WORD  # type: ignore
		var.waiters[-1].start = _ps if reg == 0 else _ps + 1
	else:
		tmp2 = var.memory_proc(val, var.WORD)
	if reg == 0:
		return _glob1c_sub(size, 0xA0 + bias) + tmp2
	return (
		_glob1c_sub(size, 0x8A - bias)
		+ [var.zero_extend(hex((reg << 3) + 6)[2:])]
		+ tmp2
	)


# If size didn't given size equals WORD.
def _mov_main(arg1: str, arg2: str, size: int | None = None) -> list[str]:
	"""
	mov <seg_reg>, <reg>
	mov <seg_reg>, <ptr>
	mov <reg>, <const>
	mov <reg>, <ptr>
	mov <reg>, <reg>
	mov <ptr>, <reg>
	mov <size> <ptr>, <const>
	mov <ptr>, <const> *Word Size*
	"""
	var.event.message_event.clear()
	tmp1, tmp2 = _convert_it(arg1, False), _convert_it(arg2)
	val1, val2 = tmp1[0], tmp2[0]
	type = (tmp1[1], tmp2[1])
	del tmp1, tmp2

	retu: list[str] = []
	tmp1 = type[0] == _REG

	if tmp1 or type[1] == _REG:
		size = val1[1] if tmp1 else val2[1]

	posiable_start = get_memory_addr() + 1 + (size == var.DWORD)

	if type == (_REG, _CONST):
		retu.append(hex(0xB0 + val1[0])[2:])
		if var.event.message_event:
			retu += ["XX"] * (size >> 1)  # type: ignore
			var.waiters[-1].size = size  # type: ignore
			var.waiters[-1].start = posiable_start
		else:
			retu += var.memory_proc(val2, size)  # type: ignore
	else:
		if tmp1:
			val1_0 = val1[0] % var.REG_INDEX_LEN
		if type == (_REG, _PTR):
			if size == -1:
				if var.event.message_event:
					retu = ["XX", "XX"]  # type: ignore
					var.waiters[-1].size = var.WORD  # type: ignore
					var.waiters[-1].start = posiable_start + 1
				else:
					retu = var.memory_proc(val2, var.WORD)  # type: ignore
				return [
					"8e",
					var.zero_extend(hex((val1_0 << 3) + 6)[2:]),  # type: ignore
				] + retu
			return _mov_sub(val1_0, val2, size, 0, posiable_start)  # type: ignore
		elif type == (_REG, _REG):
			if val1_0 == val2[0]:  # type: ignore
				var.raiseError(
					"Warning",
					"You are trying to move a register to itself.",
					False,
					index_,
				)
			if size == -1:
				# Reverse of normal register.
				return ["8e", hex(0xC0 + val2[0] + (val1_0 << 3))[2:]]  # type: ignore
			retu.append("88" if size == var.BYTE else "89")
			retu.append(hex(0xC0 + val1_0 + (val2[0] << 3))[2:])  # type: ignore
		elif type == (_PTR, _CONST):
			if size == None:
				size = var.WORD
			tmp2 = func.findSize(val2)
			if size < tmp2:
				func.overflowError(size, tmp2, index_)
			retu.append("c6" if size == var.BYTE else "c7")
			retu.append("06")
			posiable_start += 1
			isnot_did = [True, True]
			for i in range(len(var.event.message_event)):
				tmp = var.event.message_event.pop()
				if tmp == _PTR:
					isnot_did[0] = False
					retu += ["XX", "XX"]
					var.waiters[-1 if isnot_did[1] else -2].size = var.WORD
					var.waiters[-1 if isnot_did[1] else -2].start = posiable_start
				elif tmp == _CONST:
					isnot_did[1] = False
					var.waiters[-1].size = size
					var.waiters[-1].start = posiable_start + 2
			if isnot_did[0]:
				retu += var.memory_proc(val1, var.WORD)
			if isnot_did[1]:
				retu += var.memory_proc(val2, size)
			else:
				retu += ["XX"] * (size >> 1)
		elif type == (_PTR, _REG):
			if size == -1:
				if var.event.message_event:
					retu = ["XX", "XX"]
					var.waiters[-1].size = var.WORD
					var.waiters[-1].start = posiable_start + 1
				else:
					retu = var.memory_proc(val1, var.WORD)  # type: ignore
				return [
					"8c",
					var.zero_extend(hex((val2[0] << 3) + 6)[2:]),
				] + retu
			return _mov_sub(val2[0], val1, size, 2)  # type: ignore
	return [var.STR_BIT_32] + retu if size == var.DWORD else retu


def C_mov(split_: list[str]) -> list[str]:
	if split_[0][0] == ".":
		return _mov_main(split_[1][:-1], split_[2], var.sizes[split_[0][1:]])
	return _mov_main(split_[0][:-1], split_[1])


# NOTE: still dont have waiter system
# If size didn't given size equals WORD.
def _push_pop_main(
	arg: str, args: tuple[int, str, str], size: int | None = None
) -> list[str] | None:
	retu: list[str] = []
	if arg[0].isalpha():
		index, size = func.get_register(arg)
		if size == var.BYTE:
			var.raiseError("Push Error", "Cant use 8 bit registers.", line=index_)
			return
		if size == -1:
			if args[0] == 0x50:  # Push arg zero equals 0x50
				return var.push_segment_values[index]
			return var.pop_segment_values[index]
		retu.append(hex(args[0] + index)[2:])
	elif arg[0] == "*":
		retu.append(args[1])
		retu.append(args[2])
		retu += var.memory_proc(var.compute_int(arg[1:]), var.WORD)
	elif args[2] == "36":
		value = var.compute_int(arg)
		tmp = func.findSize(value)
		if not size:
			size = var.WORD
		if size < tmp:
			func.overflowError(size, tmp, index_)
		retu.append("6a" if size == var.BYTE else "68")
		retu += var.memory_proc(value, size)
	else:
		return
	return [var.STR_BIT_32] + retu if size == var.DWORD else retu


def C_push(split_: list[str]) -> list[str] | None:
	if split_[0][0] == ".":
		return _push_pop_main(
			split_[1], var.type2_inst["push"], var.sizes[split_[0][1:]]
		)
	return _push_pop_main(split_[0], var.type2_inst["push"])


def C_pop(split_: list[str]) -> list[str] | None:
	if split_[0][0] == ".":
		return _push_pop_main(
			split_[1], var.type2_inst["pop"], var.sizes[split_[0][1:]]
		)
	return _push_pop_main(split_[0], var.type2_inst["pop"])


def C_lodsx(split_: list[str]) -> list[str] | None:
	return _glob1c_sub(var.sizes[split_[0][1:]], 0xAC)


# So much simmilar with _mov_sub()
def _2input_ptr_reg_comb(  # in other words: _2input_sub(...)
	reg: int, val: int, size: int, arg: int, _ps: int = 0
) -> list[str]:
	if var.event.message_event:
		memory_value = ["XX", "XX"]
		var.waiters[-1].size = var.WORD
		var.waiters[-1].start = _ps + 1
	else:
		memory_value = var.memory_proc(val, var.WORD)
	return (
		_glob1c_sub(size, arg)  # type: ignore
		+ [var.zero_extend(hex((reg << 3) + 6)[2:])]
		+ memory_value
	)


# If size didn't given size equals WORD.
def _2input_main(
	arg1: str, arg2: str, args: tuple[Any, ...], size: int | None = None
) -> list[str] | None:
	"""
	add <a-reg>, <const>
	add <reg>, <const>
	add <non-reg8>, <const8>

	add <reg>, <reg>

	add <reg>, <ptr>

	add <ptr>, <reg>
	add <size> <ptr>, <const>
	add <ptr>, <const> *Word size*
	"""
	var.event.message_event.clear()
	tmp1, tmp2 = _convert_it(arg1), _convert_it(arg2)
	val1, val2 = tmp1[0], tmp2[0]
	type = (tmp1[1], tmp2[1])
	del tmp1, tmp2

	retu: list[str] = []
	tmp1 = type[0] == _REG

	if tmp1 or type[1] == _REG:
		size = val1[1] if tmp1 else val2[1]

	if size == -1:
		var.raiseError(
			"Segment Reg",
			"By my knowladge Segment registers can only be used in 'mov' command.",
			False,
			index_,
		)
		return

	posiable_start = get_memory_addr() + 1 + (size == var.DWORD)

	if type == (_REG, _CONST):
		is_const_byte = (
			size != var.BYTE
			and not var.event.message_event
			and func.findSize(val2) == var.BYTE
		)
		if val1[0] == 0 and not is_const_byte:
			retu.append(var.zero_extend(hex(args[0] + (size != var.BYTE))[2:]))  # type: ignore
		else:
			posiable_start += 1
			retu.append("83" if is_const_byte else ("80" if size == var.BYTE else "81"))
			retu.append(hex(args[1] + val1[0])[2:])
		if var.event.message_event:
			retu += ["XX"] * (size >> 1)  # type: ignore
			var.waiters[-1].size = size  # type: ignore
			var.waiters[-1].start = posiable_start
		else:
			retu += var.memory_proc(val2, var.BYTE if is_const_byte else size)  # type: ignore
	elif type == (_REG, _PTR):
		return _2input_ptr_reg_comb(val1[0], val2, size, args[2] + 2, posiable_start)  # type: ignore
	elif type == (_REG, _REG):
		retu.append(var.zero_extend(hex(args[2] + (size != var.BYTE))[2:]))
		retu.append(hex(0xC0 + val1[0] + (val2[0] << 3))[2:])
	elif type == (_PTR, _CONST):
		tmp2 = func.findSize(val2)
		if size == None:
			size = var.WORD
		if size < tmp2:
			func.overflowError(size, tmp2, index_)
		retu.append("80" if size == var.BYTE else "81")
		retu.append(args[3])
		posiable_start += 1
		isnot_did = [True, True]
		for i in range(len(var.event.message_event)):
			tmp = var.event.message_event.pop()
			if tmp == _PTR:
				isnot_did[0] = False
				retu += ["XX", "XX"]
				tmp3 = -1 if isnot_did[1] else -2
				var.waiters[tmp3].size = var.WORD
				var.waiters[tmp3].start = posiable_start
			elif tmp == _CONST:
				isnot_did[1] = False
				var.waiters[-1].size = size
				var.waiters[-1].start = posiable_start + 2
		if isnot_did[0]:
			retu += var.memory_proc(val1, var.WORD)
		if isnot_did[1]:
			retu += var.memory_proc(val2, size)
		else:
			retu += ["XX"] * (size >> 1)
	elif type == (_PTR, _REG):
		return _2input_ptr_reg_comb(val2[0], val1, size, args[2], posiable_start)  # type: ignore
	return [var.STR_BIT_32] + retu if size == var.DWORD else retu


def C_2input_handler(split_: list[str], command: str) -> list[str] | None:
	args = var.type3_inst[command]
	if split_[0][0] == ".":
		return _2input_main(split_[1][:-1], split_[2], args, var.sizes[split_[0][1:]])
	return _2input_main(split_[0][:-1], split_[1], args)


def C_Jcc(command: str, value: str, size: int = var.WORD):
	cmd_size = 1 + (size == var.DWORD) + (size != var.BYTE)
	number = var.compute_int(value) - cmd_size - (size >> 1) - var.addr

	if var.event.name_list:
		var.waiters.append(
			var.waiter(
				var.addr - var.orgin + cmd_size,
				number,
				index_,
				size,
			)
		)
		memory_value = ["XX"] * (size >> 1)
	else:
		memory_value = var.memory_proc(number, size)

	tmp = func.findSize(number, forge_sign=True)
	if size < tmp:
		func.overflowError(size, tmp, index_)

	return (
		([var.STR_BIT_32] if size == var.DWORD else [])
		+ (
			[hex(var.jcc_inst[command])[2:]]
			if size == var.BYTE
			else ["0f", hex(var.jcc_inst[command] + 0x10)[2:]]
		)
		+ memory_value
	)


# NOTE: still dont have waiter system for part of value
# If size didn't given size equals WORD.
def C_shift(command: str, split_: list[str]) -> list[str]:
	size = var.sizes[split_.pop(0)[1:]] if split_[0][0] == "." else var.WORD
	value = (
		1
		if len(split_) == 1
		else (-1 if split_[1] == "cl" else var.compute_int(split_[1]))
	)
	retu: list[str] = []

	split_[0] = split_[0].rstrip(",")
	if split_[0][0] == "*":
		target_addr = var.compute_int(split_[0][1:])
		retu.append(
			hex(
				(0xD3 if value == -1 else (0xD0 if value < 2 else 0xC0))
				+ (size != var.BYTE)
			)[2:]
		)
		retu.append(var.shift_inst[command][1])
		if var.event.name_list:
			var.waiters.append(
				var.waiter(
					get_memory_addr() + 2,
					target_addr,
					index_,
					var.WORD,
				)
			)
			retu += ["XX", "XX"]
		else:
			retu += var.memory_proc(target_addr, var.WORD)
	else:
		index, size = func.get_register(split_[0])
		retu.append("d3" if value == -1 else ("d1" if value < 2 else "c1"))
		retu.append(hex(var.shift_inst[command][0] + index)[2:])
	if value > 1:
		retu.append(var.zero_extend(hex(value)[2:]))
	return [var.STR_BIT_32] + retu if size == var.DWORD else retu


def _test_main(arg1: str, arg2: str, size: int = var.WORD) -> list[str] | None:
	var.event.message_event.clear()
	tmp1, tmp2 = _convert_it(arg1), _convert_it(arg2)
	val1, val2 = tmp1[0], tmp2[0]
	type = (tmp1[1], tmp2[1])
	del tmp1, tmp2

	retu: list[str] = []
	tmp1 = type[0] == _REG

	if tmp1 or type[1] == _REG:
		size = val1[1] if tmp1 else val2[1]

	if size == -1:
		return

	posiable_start = get_memory_addr() + 1 + (size == var.DWORD)

	if type == (_REG, _CONST):
		if val1[0] == 0:
			retu.append("a8" if size == var.BYTE else "a9")
		else:
			retu.append("f6" if size == var.BYTE else "f7")
			retu.append(hex(0xC0 + val1[0])[2:])
			posiable_start += 1
		if var.event.message_event:
			var.waiters[-1].size = size
			var.waiters[-1].start = posiable_start
			retu += ["XX"] * (size >> 1)
		else:
			retu += var.memory_proc(val2, size)
	elif type == (_REG, _REG):
		retu.append("84" if size == var.BYTE else "85")
		retu.append(hex(0xC0 + val1[0] + (val2[0] << 3))[2:])
	return [var.STR_BIT_32] + retu if size == var.DWORD else retu


def C_test(split_: list[str]) -> list[str] | None:
	if split_[0][0] == ".":
		return _test_main(split_[1][:-1], split_[2], var.sizes[split_[0][1:]])
	return _test_main(split_[0][:-1], split_[1])


def _mul_div_main(split_: list[str], args: tuple, size: int = var.WORD) -> list[str] | None:
	arg1 = _convert_it(split_[0])
	retu: list[str] = []
	if len(split_) == 1:
		retu.append("f6" if size == var.BYTE else "f7")
		if arg1[1] == _REG:
			retu.append(hex(args[0] + arg1[0][0])[2:])
		else:
			retu.append(args[1])
			retu += var.memory_proc(arg1[0], var.WORD)
	return [var.STR_BIT_32] + retu if size == var.DWORD else retu


def C_mul_div(split_: list[str], command: str) -> list[str] | None:
	map_func = lambda x: x.rstrip(",")
	if split_[0][0] == ".":
		return _mul_div_main(list(map(map_func, split_[1:])), var.type4_inst[command], var.sizes[split_[0][1:]])
	return _mul_div_main(list(map(map_func, split_)), var.type4_inst[command])


basic_dir = {
	"int": C_int,
	"def": C_def,
	"jmp": C_jmp,
	"call": C_call,
	"not": C_not,
	"neg": C_neg,
	"inc": C_inc,
	"dec": C_dec,
	"mov": C_mov,
	"push": C_push,
	"pop": C_pop,
	"lods": C_lodsx,
	"test": C_test,
}

command_dir = {
	"mul": C_mul_div,
	"div": C_mul_div,
}
