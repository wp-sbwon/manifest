"""
Code structure extraction for bottom-up blueprint generation.

This module extracts structural information from Python code using AST
(Abstract Syntax Tree) parsing. It identifies classes, functions, variables,
and their relationships (imports, function calls, inheritance) to generate
a blueprint that represents the actual code structure.

This bottom-up blueprint can then be compared against the top-down (intended)
blueprint to detect architectural drift.
"""
import ast
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from manifest.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Component:
    """Represents a code component extracted from source code.

    A component can be a class, function, or variable. It contains
    structural information like location, methods, attributes, and
    optional metadata about algorithms, design patterns, and complexity.

    Manifest View / Actual Code fields: detected_interface, dependencies, side_effects.
    """
    id: str
    name: str
    type: str  # "class", "function", "variable"
    file: str
    line: int
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    module_path: str = ""
    algorithm: Optional[str] = None
    design_pattern: Optional[str] = None
    complexity: Optional[str] = None
    notes: Optional[str] = None
    # Actual Code (Manifest View): signature/surface, imports used, I/O detected
    detected_interface: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    protocol_input: List[Dict[str, str]] = field(default_factory=list)
    protocol_output: List[Dict[str, str]] = field(default_factory=list)
    io_model: str = ""
    state_model: str = ""
    decorator_traits: List[str] = field(default_factory=list)


@dataclass
class Contract:
    """Represents a relationship or contract between two components.

    Contracts describe how components interact: dependencies, function calls,
    inheritance relationships, etc. They form the edges in the component
    dependency graph.

    Attributes:
        from_id: ID of the source component.
        to_id: ID of the target component.
        type: Type of relationship ("dependency", "call", "inheritance").
        symbols: List of symbols (names) involved in the relationship.
        file: Path to file where this relationship occurs.
    """
    from_id: str
    to_id: str
    type: str  # "dependency", "call", "inheritance"
    symbols: List[str] = field(default_factory=list)
    file: str = ""


class CodeExtractor:
    """Extracts code structure and generates bottom-up blueprint from source code.

    Scans Python files in a project, parses them with AST, and extracts
    components (classes, functions) and contracts (relationships) to build
    a blueprint that represents the actual code structure.

    Attributes:
        root: Root directory of the project to extract from.
        components: Dictionary mapping component IDs to Component objects.
        contracts: List of Contract objects representing relationships.
        module_map: Dictionary mapping file paths to Python module paths.
    """

    def __init__(self, root: Path = Path(".")):
        """Initialize the code extractor.

        Args:
            root: Root directory of the project. Defaults to current directory.
        """
        self.root = root
        self.components: Dict[str, Component] = {}
        self.contracts: List[Contract] = []
        self.module_map: Dict[str, str] = {}  # file_path -> module_path

    def extract_project_structure(self, root: Path = None) -> Dict[str, Any]:
        """Extract structure from entire project and generate blueprint.

        Scans all Python files in the project, extracts components and
        relationships, and generates a blueprint JSON structure that can
        be compared against the intended design blueprint.

        Args:
            root: Optional root directory. Uses self.root if not provided.

        Returns:
            Blueprint dict: version, root_id, entities (with outgoing_contracts), and metadata.
        """
        if root is None:
            root = self.root

        self.components.clear()
        self.contracts.clear()
        self.module_map.clear()

        # Find all Python files
        python_files = self._find_python_files(root)

        # Extract entities and relationships from each file
        for file_path in python_files:
            self._extract_file_structure(file_path, root)

        # Generate blueprint JSON
        return self._generate_blueprint()

    def _find_python_files(self, root: Path) -> List[Path]:
        """Find all Python files in the project directory.

        Recursively searches for .py files, excluding virtual environments,
        hidden directories, and __pycache__ directories. Test files are
        included but can be identified by their location.

        Args:
            root: Root directory to search from.

        Returns:
            List of Path objects pointing to Python files.
        """
        python_files = []
        for path in root.rglob("*.py"):
            # Skip virtual environments and hidden directories
            if any(part.startswith(".") and part != "." for part in path.parts):
                continue
            if "venv" in path.parts or "__pycache__" in path.parts:
                continue
            if "tests" in path.parts and path.name.startswith("test_"):
                # Include test files but mark them differently
                python_files.append(path)
            elif "tests" not in path.parts:
                python_files.append(path)
        return python_files

    def _extract_file_structure(self, file_path: Path, root: Path):
        """Extract structure from a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # Calculate module path
            rel_path = file_path.relative_to(root)
            module_path = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            self.module_map[str(file_path)] = module_path

            # Extract entities
            entities = self._identify_entities(tree, file_path, module_path)

            # Extract metadata (algorithm, design_pattern, complexity) for each entity
            for entity in entities:
                # Extract algorithm from code structure
                algorithm = self._extract_algorithm_from_code(tree, entity)
                if algorithm:
                    entity.algorithm = algorithm

                # Extract design pattern from structure
                design_pattern = self._extract_design_pattern_from_structure(tree, entity, entities)
                if design_pattern:
                    entity.design_pattern = design_pattern

                # Analyze complexity (always set so Inspector shows something)
                complexity = self._analyze_complexity_from_code(tree, entity)
                entity.complexity = complexity or "O(1)"

                # Infer side effects so Inspector shows them
                side_effects = self._infer_side_effects(tree, entity)
                if side_effects:
                    entity.side_effects = side_effects

                self._extract_protocol_and_profile(tree, entity)

            # Extract relationships
            relationships = self._infer_relationships(tree, file_path, module_path, entities)

            # Store components
            for entity in entities:
                self.components[entity.id] = entity

            # Store contracts
            self.contracts.extend(relationships)

        except Exception as e:
            logger.warning("Skipping unparseable file %s: %s", file_path, e)

    def _identify_entities(self, tree: ast.AST, file_path: Path, module_path: str) -> List[Component]:
        """Identify entities (classes, functions, variables) as components."""
        entities = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Extract class methods
                methods = []
                attributes = []

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                    elif isinstance(item, ast.Assign):
                        # Class attributes
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                attributes.append(target.id)

                comp_id = f"comp-{module_path}-{node.name}"
                entity = Component(
                    id=comp_id,
                    name=node.name,
                    type="class",
                    file=str(file_path),
                    line=node.lineno,
                    methods=methods,
                    attributes=attributes,
                    module_path=module_path
                )
                entities.append(entity)

            elif isinstance(node, ast.FunctionDef):
                # Check if it's a module-level function (not inside a class)
                is_module_level = True
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        if node in parent.body:
                            is_module_level = False
                            break

                if is_module_level:
                    comp_id = f"comp-{module_path}-{node.name}"
                    entity = Component(
                        id=comp_id,
                        name=node.name,
                        type="function",
                        file=str(file_path),
                        line=node.lineno,
                        module_path=module_path
                    )
                    entities.append(entity)

        return entities

    def _infer_relationships(self, tree: ast.AST, file_path: Path, module_path: str,
                           entities: List[Component]) -> List[Contract]:
        """Infer relationships between entities."""
        relationships = []

        # Build entity lookup by name
        entity_by_name: Dict[str, Component] = {}
        for entity in entities:
            entity_by_name[entity.name] = entity

        # Track imports to map external dependencies
        imports: Dict[str, str] = {}  # alias -> module

        for node in ast.walk(tree):
            # Extract imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports[alias.asname or alias.name] = alias.name

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"

            # Extract function calls
            elif isinstance(node, ast.Call):
                # Try to identify what's being called
                if isinstance(node.func, ast.Name):
                    # Direct function call: func()
                    called_name = node.func.id
                    if called_name in imports:
                        # External dependency
                        target_module = imports[called_name]
                        # Create contract for external dependency
                        relationships.append(Contract(
                            from_id=f"comp-{module_path}",
                            to_id=f"external-{target_module}",
                            type="dependency",
                            symbols=[called_name],
                            file=str(file_path)
                        ))
                    elif called_name in entity_by_name:
                        # Internal function call
                        from_entity = self._find_containing_entity(node, entities, module_path)
                        if from_entity:
                            relationships.append(Contract(
                                from_id=from_entity.id,
                                to_id=entity_by_name[called_name].id,
                                type="call",
                                symbols=[called_name],
                                file=str(file_path)
                            ))

                elif isinstance(node.func, ast.Attribute):
                    # Method call: obj.method()
                    if isinstance(node.func.value, ast.Name):
                        obj_name = node.func.value.id
                        method_name = node.func.attr

                        # Check if it's a call on an entity
                        if obj_name in entity_by_name:
                            from_entity = self._find_containing_entity(node, entities, module_path)
                            if from_entity:
                                relationships.append(Contract(
                                    from_id=from_entity.id,
                                    to_id=entity_by_name[obj_name].id,
                                    type="call",
                                    symbols=[method_name],
                                    file=str(file_path)
                                ))
                            else:
                                # Use module-level ID if no containing entity
                                from_id = f"comp-{module_path}"
                                relationships.append(Contract(
                                    from_id=from_id,
                                    to_id=entity_by_name[obj_name].id,
                                    type="call",
                                    symbols=[method_name],
                                    file=str(file_path)
                                ))

            # Extract class inheritance
            elif isinstance(node, ast.ClassDef):
                if node.bases:
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_name = base.id
                            if base_name in entity_by_name:
                                comp_id = f"comp-{module_path}-{node.name}"
                                relationships.append(Contract(
                                    from_id=comp_id,
                                    to_id=entity_by_name[base_name].id,
                                    type="inheritance",
                                    file=str(file_path)
                                ))

        # Extract import-based dependencies
        for alias, module in imports.items():
            # Create dependency contract for external imports
            from_entity = self._find_file_entity(module_path, entities)
            if from_entity:
                relationships.append(Contract(
                    from_id=from_entity.id,
                    to_id=f"external-{module}",
                    type="dependency",
                    symbols=[alias],
                    file=str(file_path)
                ))

        return relationships

    def _find_containing_entity(self, node: ast.AST, entities: List[Component],
                                module_path: str) -> Optional[Component]:
        """Find the entity that contains this AST node."""
        # This is a simplified version - in practice, we'd need to track
        # the AST node hierarchy more carefully
        # For now, return the first module-level entity or class
        for entity in entities:
            if entity.module_path == module_path:
                if entity.type == "class":
                    return entity
        for entity in entities:
            if entity.module_path == module_path and entity.type == "function":
                return entity
        return None

    def _find_file_entity(self, module_path: str, entities: List[Component]) -> Optional[Component]:
        """Find a representative entity for a module (for import dependencies)."""
        # Return first class, or first function
        for entity in entities:
            if entity.module_path == module_path:
                return entity
        # If no entity found, return None (caller should handle)
        return None

    def _extract_algorithm_from_code(self, tree: ast.AST, entity: Component) -> Optional[str]:
        """
        Extract algorithm from actual code structure patterns (conservative approach).
        Only returns if high confidence.
        """
        # Check imports for algorithm libraries
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
                    for alias in node.names:
                        imports.add(alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)

        # Check for algorithm-specific imports
        import_str = " ".join(imports).lower()
        if "dijkstra" in import_str or "networkx" in import_str:
            # Check if entity uses networkx.dijkstra_path or similar
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if "dijkstra" in node.func.attr.lower():
                            return "Dijkstra"

        # Check function/class name patterns
        name_lower = entity.name.lower()
        if "dijkstra" in name_lower:
            return "Dijkstra"
        if "bfs" in name_lower or "breadth" in name_lower:
            return "BFS"
        if "dfs" in name_lower or "depth" in name_lower:
            return "DFS"
        if "quicksort" in name_lower or "quick_sort" in name_lower:
            return "Quicksort"
        if "mergesort" in name_lower or "merge_sort" in name_lower:
            return "Mergesort"

        # Check for data structure patterns that indicate algorithms
        # Priority queue + distance dict -> Dijkstra-like
        has_heapq = "heapq" in import_str
        has_distance_tracking = False

        # Look for distance/cost tracking patterns in the entity's code
        entity_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name == entity.name:
                    entity_node = node
                    break

        if entity_node:
            # Check for distance/cost tracking
            for node in ast.walk(entity_node):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if "distance" in target.id.lower() or "cost" in target.id.lower():
                                has_distance_tracking = True
                                break

            if has_heapq and has_distance_tracking:
                return "Dijkstra"

        return None

    def _extract_design_pattern_from_structure(self, tree: ast.AST, entity: Component,
                                             all_entities: List[Component]) -> Optional[str]:
        """
        Extract design pattern from code structure analysis (conservative approach).
        """
        # Find the entity's AST node
        entity_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name == entity.name:
                    entity_node = node
                    break

        if not entity_node:
            return None

        # Singleton Pattern: __new__ override
        if isinstance(entity_node, ast.ClassDef):
            has_new = False
            for item in entity_node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__new__":
                    has_new = True
                    break
            if has_new:
                return "Singleton"

            # Factory Pattern: create_* or make_* methods
            create_methods = []
            for item in entity_node.body:
                if isinstance(item, ast.FunctionDef):
                    if item.name.startswith("create_") or item.name.startswith("make_"):
                        create_methods.append(item.name)
            if len(create_methods) >= 2:
                return "Factory"

            # Strategy Pattern: Interface + multiple implementations
            # Check if this class has abstract methods (ABC)
            has_abstract = False
            for base in entity_node.bases:
                if isinstance(base, ast.Name):
                    if "ABC" in base.id or "Abstract" in base.id:
                        has_abstract = True
                        break

            if has_abstract:
                # Check for abstract methods
                for item in entity_node.body:
                    if isinstance(item, ast.FunctionDef):
                        for decorator in item.decorator_list:
                            if isinstance(decorator, ast.Name):
                                if "abstractmethod" in decorator.id.lower():
                                    return "Strategy"

            # Check if multiple classes implement the same interface (heuristic; full context would improve accuracy)
            if entity.type == "class":
                # Check for interface-like patterns
                if len(entity.methods) > 0:
                    # Look for other entities with similar method signatures
                    similar_count = 0
                    for other_entity in all_entities:
                        if other_entity.id != entity.id and other_entity.type == "class":
                            # Check if they share methods (simplified)
                            shared_methods = set(entity.methods) & set(other_entity.methods)
                            if len(shared_methods) >= 2:
                                similar_count += 1
                    if similar_count >= 2:
                        return "Strategy"

        return None

    def _analyze_complexity_from_code(self, tree: ast.AST, entity: Component) -> Optional[str]:
        """
        Analyze code complexity from loop structures (conservative approach).
        """
        # Find the entity's AST node
        entity_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name == entity.name:
                    entity_node = node
                    break

        if not entity_node:
            return None

        # Count nested loops
        max_nesting = 0
        current_nesting = 0

        def count_nesting(node: ast.AST, level: int = 0):
            """Count nesting level of control structures in AST node.

            Recursively traverses the AST to count nested control structures
            (for, while loops) which indicate code complexity. Updates the
            max_nesting variable in the outer scope.

            Args:
                node: AST node to analyze.
                level: Current nesting level (incremented for loops).
            """
            nonlocal max_nesting
            if isinstance(node, (ast.For, ast.While)):
                level += 1
                max_nesting = max(max_nesting, level)
            for child in ast.iter_child_nodes(node):
                count_nesting(child, level)

        count_nesting(entity_node)

        # Simple heuristics (always return a value so Inspector shows something)
        if max_nesting == 0:
            has_recursion = self._has_recursion(tree, entity)
            if has_recursion:
                return "O(n)"
            return "O(1)"
        elif max_nesting == 1:
            return "O(n)"
        elif max_nesting == 2:
            return "O(n²)"
        elif max_nesting >= 3:
            return "O(n³)"

        return None

    def _has_recursion(self, tree: ast.AST, entity: Component) -> bool:
        """Check for recursive function calls."""
        # Find the entity's AST node
        entity_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name == entity.name:
                    entity_node = node
                    break

        if not entity_node:
            return False

        # Get function names in this entity
        function_names = set()
        for node in ast.walk(entity_node):
            if isinstance(node, ast.FunctionDef):
                function_names.add(node.name)

        # Check for self-recursive calls
        for node in ast.walk(entity_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in function_names:
                        return True

        return False

    def _infer_side_effects(self, tree: ast.AST, entity: Component) -> List[str]:
        """Infer side effects from entity AST so Inspector can show them."""
        entity_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == entity.name:
                entity_node = node
                break
        if not entity_node:
            return []
        effects: Set[str] = set()
        for node in ast.walk(entity_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                    if name == "open":
                        effects.add("file_io")
                    elif name == "print":
                        effects.add("stdout")
                elif isinstance(node.func, ast.Attribute):
                    attr = node.func.attr.lower()
                    obj = node.func.value
                    if isinstance(obj, ast.Name):
                        mod = obj.id.lower()
                        if "logging" in mod or attr in ("info", "debug", "warning", "error", "log"):
                            effects.add("logging")
                        if mod in ("requests", "urllib", "http") or "request" in mod:
                            effects.add("network")
                        if mod == "subprocess":
                            effects.add("subprocess")
                    if attr in ("write", "read", "readline", "readlines") or "file" in attr:
                        effects.add("file_io")
        return sorted(effects)

    def _extract_protocol_and_profile(self, tree: ast.AST, entity: Component) -> None:
        entity_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == entity.name:
                entity_node = node
                break
        if not entity_node:
            return
        fn = entity_node
        if isinstance(entity_node, ast.ClassDef):
            for item in entity_node.body:
                if isinstance(item, ast.FunctionDef) and item.name in ("__init__", "__new__"):
                    fn = item
                    break
            else:
                for item in entity_node.body:
                    if isinstance(item, ast.FunctionDef):
                        fn = item
                        break
        if not isinstance(fn, ast.FunctionDef):
            return
        for dec in fn.decorator_list:
            if isinstance(dec, ast.Name):
                entity.decorator_traits.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                entity.decorator_traits.append(dec.attr)
        if getattr(fn, "args", None):
            for arg in fn.args.args:
                if arg.arg != "self":
                    t = ast.unparse(arg.annotation) if hasattr(ast, "unparse") and arg.annotation else ""
                    entity.protocol_input.append({"name": arg.arg, "type": t})
        if fn.returns:
            t = ast.unparse(fn.returns) if hasattr(ast, "unparse") else ""
            entity.protocol_output.append({"name": "return", "type": t or ""})
        if isinstance(fn, ast.FunctionDef):
            async_fn = getattr(ast, "AsyncFunctionDef", None)
            if async_fn and isinstance(fn, async_fn):
                entity.io_model = "async"
            elif any(isinstance(n, ast.Yield) for n in ast.walk(fn)):
                entity.io_model = "generator"
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                        entity.state_model = "mutable"
                        break

    def _generate_blueprint(self) -> Dict[str, Any]:
        """Generate blueprint dict: version, root_id, entities with outgoing_contracts."""
        from datetime import datetime
        from manifest.audit.entity_schema import empty_entity, PROJECT_ROOT_ID as ROOT_ID

        entity_ids = {c.id for c in self.components.values()}
        comp_deps: Dict[str, List[str]] = {c.id: [] for c in self.components.values()}
        for contract in self.contracts:
            if contract.to_id.startswith("external-"):
                mod = contract.to_id.replace("external-", "", 1).strip()
                if mod and mod not in comp_deps.get(contract.from_id, []):
                    comp_deps.setdefault(contract.from_id, []).append(mod)
            elif contract.to_id in entity_ids:
                if contract.to_id not in comp_deps.get(contract.from_id, []):
                    comp_deps.setdefault(contract.from_id, []).append(contract.to_id)

        by_module: Dict[str, List[str]] = {}
        for comp in self.components.values():
            mp = comp.module_path or ""
            by_module.setdefault(mp, []).append(comp.id)
        file_level_deps: Dict[str, Set[str]] = {}
        for mp, cids in by_module.items():
            all_deps: Set[str] = set()
            for cid in cids:
                all_deps.update(comp_deps.get(cid, []))
            file_level_deps[mp] = all_deps
        for comp in self.components.values():
            mp = comp.module_path or ""
            for d in file_level_deps.get(mp, []):
                if d not in comp_deps.get(comp.id, []):
                    comp_deps.setdefault(comp.id, []).append(d)

        # Outgoing contracts per entity (from_id -> list of {to, type, file, symbols})
        by_from: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for contract in self.contracts:
            by_from[contract.from_id].append({
                "to": contract.to_id,
                "type": contract.type,
                "file": contract.file or "",
                "symbols": list(contract.symbols or []),
            })

        root_children: List[str] = []
        entities: List[Dict[str, Any]] = []
        for comp in self.components.values():
            root_children.append(comp.id)
            det_iface = (
                comp.detected_interface
                if comp.detected_interface
                else (f"{comp.name}({', '.join(comp.methods or [])})" if comp.type == "class" else f"{comp.name}()")
            )
            traits = list(getattr(comp, "side_effects", []) or [])
            traits.extend(getattr(comp, "decorator_traits", []) or [])
            if comp.complexity:
                traits.append(f"complexity:{comp.complexity}")
            protocol_input = getattr(comp, "protocol_input", None) or []
            protocol_output = getattr(comp, "protocol_output", None) or []
            if not protocol_output and det_iface:
                protocol_output = [{"name": "signature", "type": "string"}]
            entity = dict(empty_entity(comp.id))
            entity["id"] = comp.id
            entity["children"] = []
            entity["dependencies"] = comp_deps.get(comp.id, [])
            entity["outgoing_contracts"] = by_from.get(comp.id, [])
            entity["symbol"] = (comp.file or comp.module_path or "")[:500]
            entity["protocol"] = {"input": protocol_input, "output": protocol_output}
            entity["profile"] = {
                "language": "python",
                "platform": "",
                "io_model": getattr(comp, "io_model", "") or "",
                "state_model": getattr(comp, "state_model", "") or "",
            }
            entity["traits"] = traits
            entity["topology_actual"] = {"type": "", "map": []}
            entity["preview"] = ""
            entities.append(entity)

        root_entity = dict(empty_entity(ROOT_ID))
        root_entity["id"] = ROOT_ID
        root_entity["children"] = root_children
        root_entity["dependencies"] = []
        root_entity["outgoing_contracts"] = []
        entities.insert(0, root_entity)

        result = {
            "version": "1.0",
            "root_id": ROOT_ID,
            "entities": entities,
            "source": "code_extraction",
            "ground_truth": True,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "ast_parsing",
        }
        from manifest.audit.entity_validation import normalize_for_schema
        return normalize_for_schema(result)

    def save_blueprint(self, blueprint: Dict[str, Any], output_path: Path) -> bool:
        """Save blueprint to file with metadata. Validates before write; aborts on failure."""
        from manifest.audit.entity_validation import validate_blueprint_data
        from manifest.audit.blueprint.blueprint_metadata import save_blueprint_with_metadata
        valid, errors = validate_blueprint_data(blueprint)
        if not valid and errors:
            from manifest.core.logger import get_logger
            get_logger(__name__).error("Blueprint validation failed: %s", errors)
            return False
        return save_blueprint_with_metadata(
            blueprint, output_path, "code_extraction", True, "ast_parsing"
        )
