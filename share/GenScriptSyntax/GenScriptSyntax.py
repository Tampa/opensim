import os
import sys
import hashlib
import uuid

validnames = {"os", "ll", "ls"}
totrim = [' ', '\t']
spacesplit = ' '
commasplit = ','


class ConstInfo:
	def __init__(self, name, type_, value, desc):
		self.name = name
		self.type = type_
		self.value = value
		self.desc = desc


class ArgsInfo:
	def __init__(self, name, type_):
		self.name = name
		self.type = type_


class FunctionInfo:
	def __init__(self, name, type_, args, desc):
		self.name = name
		self.type = type_
		self.args = args
		self.desc = desc


def type_to_string(t):
	ts = t.lower()
	if '.' in ts:
		ts = ts.split('.')[-1]
	return {
		"bool": "integer", "boolean": "integer", "int": "integer", "int32": "integer", "int64": "integer",
		"lslinteger": "integer", "lsl_integer": "integer", "float": "float", "double": "float",
		"lslfloat": "float", "lsl_float": "float", "string": "string", "lslstring": "string",
		"lsl_string": "string", "readonlyspan<char>": "string", "key": "key", "lslkey": "key",
		"lsl_key": "key", "quaternion": "rotation", "rotation": "rotation", "lslrotation": "rotation",
		"lsl_rotation": "rotation", "vector": "vector", "lslvector": "vector", "lsl_vector": "vector",
		"vector3": "vector", "list": "list", "lsllist": "list", "lsl_list": "list", "void": ""
	}.get(ts, "")


def set_empty():
	return ""


def read_script_base(p):
	try:
		with open(os.path.join(os.path.dirname(os.path.realpath(p)), "ScriptSyntaxBase.xml"), "r") as f:
			return f.read()
	except:
		print("Problem reading ScriptSyntaxBase.xml")
		sys.exit(-1)


def compare_by_name_const(a):
	return a.name


def compare_by_name_func(a):
	return a.name.lower()


def parse_const(sb, path):
	constants = []
	lastdesc = ""
	try:
		const_path = os.path.join(path, "LSL_Constants.cs")
		if not os.path.exists(const_path):
			raise Exception("Unable to open LSL_Constants.cs")
		with open(const_path, "r") as f:
			for line in f:
				name = type_ = value = ""
				line = line.strip()
				if line.startswith("//ApiDesc "):
					lastdesc += ("&#xA;" if lastdesc else "") + line[10:]
					continue
				if '=' not in line or ';' not in line:
					lastdesc = ""
					continue
				value = line.split('=')[1].split(';')[0].strip()
				decl = line.split('=')[0].strip()
				if decl.startswith("public static readonly "):
					parts = decl[len("public static readonly "):].split()
					if len(parts) != 2:
						continue
					type_, name = map(str.strip, parts)
				elif decl.startswith("public const "):
					parts = decl[len("public const "):].split()
					if len(parts) != 2:
						continue
					type_, name = map(str.strip, parts)
				else:
					continue
				type_ = type_to_string(type_)
				if not name or not type_:
					continue
				if type_ == "string" and value.startswith('"') and value.endswith('"'):
					value = value[1:-1].replace("\\u", "U+")
				elif type_ == "float":
					value = value.replace("f", "")
				elif type_ in {"vector", "rotation"}:
					if value == "ZERO_VECTOR":
						value = "&gt;0,0,0&lt;"
					else:
						inside = value[value.find("(")+1:value.find(")")]
						value = "&gt;" + inside.replace(" ", "") + "&lt;"
				constants.append(ConstInfo(name, type_, value, lastdesc))
				lastdesc = ""
	except Exception as e:
		raise Exception("Error " + str(e))

	constants.sort(key=compare_by_name_const)
	sb.append("<key>constants</key>\n<map>\n")
	for c in constants:
		sb.append(f" <key>{c.name}</key><map>\n")
		sb.append(f"  <key>type</key><string>{c.type}</string>\n")
		sb.append(f"  <key>value</key><string>{c.value}</string>\n")
		if c.desc:
			sb.append(f"  <key>tooltip</key><string>{c.desc}</string>\n")
		sb.append(" </map>\n")
	sb.append("</map>\n")


def parse_function_file(functions, file, path):
	lastdesc = ""
	try:
		filepath = os.path.join(path, file)
		if not os.path.exists(filepath):
			raise Exception("Unable to find " + file)
		with open(filepath, "r") as f:
			for line in f:
				type_ = name = args_str = ""
				line = line.strip()
				if line.startswith("*") or line.startswith("/*") or line.startswith("//"):
					if line.startswith("//ApiDesc "):
						lastdesc += ("&#xA;" if lastdesc else "") + line[10:]
					continue
				if '(' not in line or ')' not in line:
					lastdesc = ""
					continue
				args_str = line[line.find("(")+1:line.find(")")]
				parts = line[:line.find("(")].strip().split()
				if len(parts) >= 2:
					type_, name = parts[0], parts[-1]
				elif len(parts) == 1:
					name = parts[0]
					type_ = ""
				else:
					lastdesc = ""
					continue
				if name[:2].lower() not in validnames:
					lastdesc = ""
					continue
				args = []
				if args_str:
					for arg in args_str.split(commasplit):
						arg_parts = arg.strip().split()
						if len(arg_parts) == 2:
							args.append(ArgsInfo(arg_parts[1], type_to_string(arg_parts[0])))
						elif len(arg_parts) == 1:
							args.append(ArgsInfo("", type_to_string(arg_parts[0])))
				functions.append(FunctionInfo(name, type_to_string(type_), args, lastdesc))
				lastdesc = ""
	except Exception as e:
		raise Exception("Error " + str(e))


def parse_functions(sb, path):
	functions = []
	for file in ["ILSL_Api.cs", "ILS_Api.cs", "IOSSL_Api.cs"]:
		parse_function_file(functions, file, path)
	functions.sort(key=compare_by_name_func)
	sb.append("<key>functions</key>\n<map>\n")
	for f in functions:
		sb.append(f" <key>{f.name}</key>\n <map>\n")
		if f.type:
			sb.append(f"  <key>return</key><string>{f.type}</string>\n")
		if not f.args:
			sb.append("  <key>arguments</key><undef/>\n")
		else:
			sb.append("  <key>arguments</key><array>\n")
			for a in f.args:
				sb.append(f"   <map><key>{a.name}</key><map><key>type</key><string>{a.type}</string></map></map>\n")
			sb.append("  </array>\n")
		if f.desc:
			sb.append(f"  <key>tooltip</key><string>{f.desc}</string>\n")
		sb.append(" </map>\n")
	sb.append("</map>\n")


def main():
	if len(sys.argv) > 1:
		opensim_base = sys.argv[1]
		if not os.path.exists(opensim_base):
			print("Could not find folder", opensim_base)
			sys.exit(-1)
		api_base = os.path.join(opensim_base, "OpenSim", "Region", "ScriptEngine", "Shared", "Api")
		interface_path = os.path.join(api_base, "Interface")
		runtime_path = os.path.join(api_base, "Runtime")
		print("Looking for interface source files in", interface_path)
		print("Looking for runtime source files in", runtime_path)
		output_path = sys.argv[2] if len(sys.argv) == 3 else ""
		if output_path and not os.path.exists(output_path):
			print("Could not find output folder")
			sys.exit(-1)
		print("Will write to folder", output_path)
	else:
		runtime_path = r"D:\opensim\opensim\OpenSim\Region\ScriptEngine\Shared\Api\Runtime"
		interface_path = r"D:\opensim\opensim\OpenSim\Region\ScriptEngine\Shared\Api\Interface"
		output_path = ""

	if not os.path.exists(runtime_path) or not os.path.exists(interface_path):
		print("Could not find folder", runtime_path if not os.path.exists(runtime_path) else interface_path)
		sys.exit(-1)

	sb = ["<llsd><map><key>llsd-lsl-syntax-version</key><integer>2</integer>\n"]
	sb.append(read_script_base(sys.argv[0]))
	parse_const(sb, runtime_path)
	parse_functions(sb, interface_path)
	sb.append("</map></llsd>")
	outstr = ''.join(sb)
	digest = hashlib.sha1(outstr.encode('utf-8')).digest()[:16]
	id_ = uuid.UUID(bytes=digest)

	if output_path:
		with open(os.path.join(output_path, "ScriptSyntax.xml"), "w") as f:
			f.write(f"{id_}\n{outstr}")
		print("Wrote file ScriptSyntax.xml")


if __name__ == "__main__":
	main()
