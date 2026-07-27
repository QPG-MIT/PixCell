"""
Weber Script Analyzer

Parses GDSFactory Python scripts using AST to extract:
- Component instantiations (gf.components.*)
- Numeric parameters
- Layer assignments
- Cross-section definitions
- Component connections
"""

import ast
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set


@dataclass
class ParameterInfo:
    """Information about a numeric parameter found in the script."""
    name: str                    # Variable or parameter name
    value: float                 # Numeric value
    line_number: int             # Line in source file
    context: str                 # "function_param" | "variable" | "argument"
    parent_function: Optional[str] = None  # Containing function name
    suggested_range: Tuple[float, float, float] = None  # (min, max, step)


@dataclass
class ComponentInfo:
    """Information about a GDSFactory component instantiation."""
    id: str                      # Unique identifier (variable name)
    type: str                    # Component type (e.g., "straight", "bend_circular")
    full_call: str               # Full function call (e.g., "gf.components.straight")
    params: Dict[str, Any]       # Parameters passed to the component
    layer: Optional[Tuple[int, int]] = None  # Layer if specified
    line_number: int = 0
    parent_function: Optional[str] = None


@dataclass
class CrossSectionInfo:
    """Information about a cross-section definition."""
    name: str                    # Variable name
    width: Optional[float] = None
    layer: Optional[Tuple[int, int]] = None
    radius: Optional[float] = None
    line_number: int = 0


@dataclass
class ConnectionInfo:
    """Information about a component connection."""
    source_ref: str              # Source reference variable
    source_port: str             # Source port name
    target_ref: str              # Target reference variable
    target_port: str             # Target port name
    line_number: int = 0


@dataclass
class FunctionInfo:
    """Information about a function definition."""
    name: str
    parameters: List[Dict[str, Any]]  # List of {name, default, annotation}
    decorators: List[str]
    line_number: int
    end_line_number: int = 0  # Line where function ends
    returns_component: bool = False


@dataclass
class ScriptAnalysis:
    """Complete analysis result of a GDSFactory script."""
    script_path: str
    components: List[ComponentInfo] = field(default_factory=list)
    parameters: List[ParameterInfo] = field(default_factory=list)
    layers: List[Tuple[int, int]] = field(default_factory=list)
    cross_sections: List[CrossSectionInfo] = field(default_factory=list)
    connections: List[ConnectionInfo] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    main_function: Optional[str] = None

    def to_json(self) -> str:
        """Serialize analysis to JSON string."""
        return json.dumps(asdict(self), indent=2, default=str)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def get_main_function_info(self) -> Optional[FunctionInfo]:
        """Get the main component function info."""
        if self.main_function:
            for func in self.functions:
                if func.name == self.main_function:
                    return func
        return None

    def get_tunable_parameters(self) -> List[ParameterInfo]:
        """Tunable knobs for sliders.

        Module-level ``name = value`` assignments are the parametric
        contract's mandated knob shape (the main function reads them as
        globals), so they come first; the main function's own numeric
        parameters are included as well. Deduplicated by name.
        """
        main_func = self.main_function
        seen: set = set()
        out: List[ParameterInfo] = []
        for p in self.parameters:
            is_module_level = p.context == "variable" and p.parent_function is None
            is_main_param = p.parent_function == main_func and p.context == "function_param"
            if (is_module_level or is_main_param) and p.name not in seen:
                seen.add(p.name)
                out.append(p)
        return out


class GDSFactoryVisitor(ast.NodeVisitor):
    """AST visitor that extracts GDSFactory-specific patterns."""

    def __init__(self):
        self.components: List[ComponentInfo] = []
        self.parameters: List[ParameterInfo] = []
        self.layers: Set[Tuple[int, int]] = set()
        self.cross_sections: List[CrossSectionInfo] = []
        self.connections: List[ConnectionInfo] = []
        self.functions: List[FunctionInfo] = []

        # Tracking state
        self.current_function: Optional[str] = None
        self.variable_assignments: Dict[str, Any] = {}

        # Counter for generating unique IDs for inline components
        self._inline_component_counter: Dict[str, int] = {}

        # Track BinOp nodes that have been handled (to avoid duplicates)
        self._handled_binops: Set[int] = set()

    def _generate_unique_id(self, comp_type: str, line_no: int) -> str:
        """Generate a unique ID for an inline component."""
        # Create a base ID from component type and line number
        base_id = f"{comp_type}_L{line_no}"

        # Check if we've seen this base before
        if base_id not in self._inline_component_counter:
            self._inline_component_counter[base_id] = 0
            return base_id

        # Increment counter and append suffix
        self._inline_component_counter[base_id] += 1
        return f"{base_id}_{self._inline_component_counter[base_id]}"

    def _extract_component_from_binop(self, node: ast.BinOp) -> Optional[ast.Call]:
        """Extract component call from a << BinOp if present."""
        if isinstance(node.op, ast.LShift) and isinstance(node.right, ast.Call):
            return node.right
        return None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definitions."""
        old_function = self.current_function
        self.current_function = node.name

        # Extract function info
        params = []
        for arg in node.args.args:
            param_info = {"name": arg.arg}

            # Get annotation if present
            if arg.annotation:
                param_info["annotation"] = ast.unparse(arg.annotation)

            params.append(param_info)

        # Get defaults
        defaults = node.args.defaults
        num_defaults = len(defaults)
        num_args = len(node.args.args)

        for i, default in enumerate(defaults):
            arg_index = num_args - num_defaults + i
            if arg_index >= 0 and arg_index < len(params):
                try:
                    params[arg_index]["default"] = ast.literal_eval(default)

                    # Record as parameter if numeric
                    value = params[arg_index]["default"]
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        self.parameters.append(ParameterInfo(
                            name=params[arg_index]["name"],
                            value=float(value),
                            line_number=node.lineno,
                            context="function_param",
                            parent_function=node.name
                        ))
                except (ValueError, TypeError):
                    params[arg_index]["default"] = ast.unparse(default)

        # Get decorators
        decorators = [ast.unparse(d) for d in node.decorator_list]

        # Check if returns component
        returns_component = any(
            dec in ["gf.cell", "@gf.cell"] or "cell" in dec.lower()
            for dec in decorators
        )

        # Calculate end line number
        end_lineno = node.end_lineno if hasattr(node, 'end_lineno') else node.lineno

        self.functions.append(FunctionInfo(
            name=node.name,
            parameters=params,
            decorators=decorators,
            line_number=node.lineno,
            end_line_number=end_lineno,
            returns_component=returns_component
        ))

        # Visit children
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Assign(self, node: ast.Assign):
        """Visit variable assignments."""
        # Handle single target assignments
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id

            # Try to evaluate the value
            try:
                value = ast.literal_eval(node.value)
                self.variable_assignments[var_name] = value

                # Check if it's a numeric value (potential parameter)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    self.parameters.append(ParameterInfo(
                        name=var_name,
                        value=float(value),
                        line_number=node.lineno,
                        context="variable",
                        parent_function=self.current_function
                    ))

                # Check if it's a layer tuple
                if isinstance(value, tuple) and len(value) == 2:
                    if all(isinstance(v, int) for v in value):
                        self.layers.add(value)

            except (ValueError, TypeError):
                pass

            # Check for << operator pattern: ref = c << component
            if isinstance(node.value, ast.BinOp):
                comp_call = self._extract_component_from_binop(node.value)
                if comp_call is not None:
                    # Mark this BinOp as handled to avoid duplicate processing
                    self._handled_binops.add(id(node.value))
                    # Use the variable name as the component ID
                    self._check_component_call(var_name, comp_call, node.lineno)
                    # Don't process further - we've handled this
                    self.generic_visit(node)
                    return

            # Check for component instantiation (direct assignment)
            self._check_component_call(var_name, node.value, node.lineno)

            # Check for cross-section definition
            self._check_cross_section(var_name, node.value, node.lineno)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Visit type-annotated assignments such as ``slices: int = 26``.

        Annotated top-level dimensions are part of the same parametric
        contract as plain assignments.  Keeping them in the Weber analysis is
        also what lets downstream consumers preserve integer-only counts.
        """
        if isinstance(node.target, ast.Name) and node.value is not None:
            var_name = node.target.id
            try:
                value = ast.literal_eval(node.value)
                self.variable_assignments[var_name] = value
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    self.parameters.append(ParameterInfo(
                        name=var_name,
                        value=float(value),
                        line_number=node.lineno,
                        context="variable",
                        parent_function=self.current_function,
                    ))
                if (isinstance(value, tuple) and len(value) == 2
                        and all(isinstance(v, int) for v in value)):
                    self.layers.add(value)
            except (ValueError, TypeError):
                pass

            self._check_component_call(var_name, node.value, node.lineno)
            self._check_cross_section(var_name, node.value, node.lineno)

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr):
        """Visit expression statements (e.g., method calls)."""
        if isinstance(node.value, ast.Call):
            self._check_connection(node.value, node.lineno)
            self._check_component_ref(node.value, node.lineno)

        self.generic_visit(node)

    def _check_component_call(self, var_name: str, value_node: ast.expr, line_no: int):
        """Check if a value is a gf.components.* call."""
        if not isinstance(value_node, ast.Call):
            return

        # Get the full call string
        try:
            call_str = ast.unparse(value_node.func)
        except Exception:
            return

        # Check for gf.components.*
        if "gf.components." in call_str or "gdsfactory.components." in call_str:
            # Extract component type
            parts = call_str.split(".")
            comp_type = parts[-1] if parts else "unknown"

            # Extract parameters
            params = self._extract_call_params(value_node)

            # Check for layer in params
            layer = None
            if "layer" in params:
                layer_val = params["layer"]
                if isinstance(layer_val, tuple) and len(layer_val) == 2:
                    layer = layer_val
                    self.layers.add(layer)

            self.components.append(ComponentInfo(
                id=var_name,
                type=comp_type,
                full_call=call_str,
                params=params,
                layer=layer,
                line_number=line_no,
                parent_function=self.current_function
            ))

    def _check_cross_section(self, var_name: str, value_node: ast.expr, line_no: int):
        """Check if a value is a cross-section definition."""
        if not isinstance(value_node, ast.Call):
            return

        try:
            call_str = ast.unparse(value_node.func)
        except Exception:
            return

        if "cross_section" in call_str.lower():
            params = self._extract_call_params(value_node)

            self.cross_sections.append(CrossSectionInfo(
                name=var_name,
                width=params.get("width"),
                layer=params.get("layer"),
                radius=params.get("radius"),
                line_number=line_no
            ))

    def _check_connection(self, call_node: ast.Call, line_no: int):
        """Check if a call is a port connection."""
        if not isinstance(call_node.func, ast.Attribute):
            return

        method_name = call_node.func.attr

        if method_name == "connect" and len(call_node.args) >= 1:
            # Get the source reference
            if isinstance(call_node.func.value, ast.Name):
                source_ref = call_node.func.value.id
            else:
                source_ref = ast.unparse(call_node.func.value)

            # Get the source port (first argument)
            try:
                source_port = ast.literal_eval(call_node.args[0])
            except (ValueError, TypeError):
                source_port = ast.unparse(call_node.args[0])

            # Get the target (second argument)
            target_ref = "unknown"
            target_port = "unknown"
            if len(call_node.args) >= 2:
                target_expr = call_node.args[1]
                # Try to parse X.ports["Y"]
                if isinstance(target_expr, ast.Subscript):
                    if isinstance(target_expr.value, ast.Attribute):
                        if target_expr.value.attr == "ports":
                            if isinstance(target_expr.value.value, ast.Name):
                                target_ref = target_expr.value.value.id
                            try:
                                target_port = ast.literal_eval(target_expr.slice)
                            except (ValueError, TypeError):
                                target_port = ast.unparse(target_expr.slice)

            self.connections.append(ConnectionInfo(
                source_ref=source_ref,
                source_port=str(source_port),
                target_ref=target_ref,
                target_port=str(target_port),
                line_number=line_no
            ))

    def _check_component_ref(self, call_node: ast.Call, line_no: int):
        """Check for << operator component references (handled as BinOp)."""
        pass  # << is handled in visit_BinOp

    def visit_BinOp(self, node: ast.BinOp):
        """Visit binary operations (for << component references)."""
        if isinstance(node.op, ast.LShift):
            # Skip if this BinOp was already handled in visit_Assign
            if id(node) in self._handled_binops:
                self.generic_visit(node)
                return

            # This is c << component pattern (standalone, not assigned to variable)
            if isinstance(node.right, ast.Call):
                # Extract component type to generate a meaningful ID
                try:
                    call_str = ast.unparse(node.right.func)
                    if "gf.components." in call_str or "gdsfactory.components." in call_str:
                        parts = call_str.split(".")
                        comp_type = parts[-1] if parts else "component"
                    else:
                        comp_type = "component"
                except Exception:
                    comp_type = "component"

                # Generate unique ID
                unique_id = self._generate_unique_id(comp_type, node.lineno)
                self._check_component_call(unique_id, node.right, node.lineno)
            elif isinstance(node.right, ast.Name):
                # Reference to existing component variable
                pass

        self.generic_visit(node)

    def _extract_call_params(self, call_node: ast.Call) -> Dict[str, Any]:
        """Extract parameters from a function call."""
        params = {}

        # Positional arguments
        for i, arg in enumerate(call_node.args):
            try:
                params[f"_arg{i}"] = ast.literal_eval(arg)
            except (ValueError, TypeError):
                params[f"_arg{i}"] = ast.unparse(arg)

        # Keyword arguments
        for kw in call_node.keywords:
            if kw.arg:
                try:
                    params[kw.arg] = ast.literal_eval(kw.value)
                except (ValueError, TypeError):
                    params[kw.arg] = ast.unparse(kw.value)

        return params


def analyze_script(script_path: str) -> ScriptAnalysis:
    """
    Analyze a GDSFactory script and extract component/parameter information.

    Args:
        script_path: Path to the Python script

    Returns:
        ScriptAnalysis object containing extracted information
    """
    path = Path(script_path)
    if not path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    source = path.read_text()
    tree = ast.parse(source)

    visitor = GDSFactoryVisitor()
    visitor.visit(tree)

    # Find main function (decorated with @gf.cell or named create_*, main, etc.)
    main_function = None
    for func in visitor.functions:
        if func.returns_component:
            main_function = func.name
            break
        if func.name.startswith("create_") or func.name == "main":
            main_function = func.name

    # Add suggested ranges to parameters
    from .config import suggest_slider_range
    for param in visitor.parameters:
        param.suggested_range = suggest_slider_range(param.value, param.name)

    return ScriptAnalysis(
        script_path=str(path.absolute()),
        components=visitor.components,
        parameters=visitor.parameters,
        layers=list(visitor.layers),
        cross_sections=visitor.cross_sections,
        connections=visitor.connections,
        functions=visitor.functions,
        main_function=main_function
    )


def analyze_script_from_source(source: str, name: str = "<source>") -> ScriptAnalysis:
    """
    Analyze GDSFactory script from source string.

    Args:
        source: Python source code string
        name: Name to use for the script

    Returns:
        ScriptAnalysis object
    """
    tree = ast.parse(source)

    visitor = GDSFactoryVisitor()
    visitor.visit(tree)

    # Find main function
    main_function = None
    for func in visitor.functions:
        if func.returns_component:
            main_function = func.name
            break

    # Keep the in-memory path behavior identical to analyze_script().  All
    # HOMI consumers analyze source strings, and without these ranges a zero
    # default collapses to an unusable 0..0 slider downstream.
    from .config import suggest_slider_range
    for param in visitor.parameters:
        param.suggested_range = suggest_slider_range(param.value, param.name)

    return ScriptAnalysis(
        script_path=name,
        components=visitor.components,
        parameters=visitor.parameters,
        layers=list(visitor.layers),
        cross_sections=visitor.cross_sections,
        connections=visitor.connections,
        functions=visitor.functions,
        main_function=main_function
    )
