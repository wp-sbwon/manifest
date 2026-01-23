"""
Code Extractor - Extracts code structure and generates bottom-up blueprint.
Uses AST parsing to identify entities (classes, functions, variables) and
infer relationships (imports, calls, inheritance) to create blueprint.json.
"""
import ast
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class Component:
    """Represents a code component (class, function, or variable)."""
    id: str
    name: str
    type: str  # "class", "function", "variable"
    file: str
    line: int
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    module_path: str = ""
    # Note: methodology removed - it's a development methodology, not product logic
    algorithm: Optional[str] = None  # e.g., "Dijkstra", "BFS" (product logic only)
    design_pattern: Optional[str] = None  # e.g., "Strategy", "Factory" (product logic only)
    complexity: Optional[str] = None  # e.g., "O(n log n)" (product logic only)
    notes: Optional[str] = None


@dataclass
class Contract:
    """Represents a relationship between components."""
    from_id: str
    to_id: str
    type: str  # "dependency", "call", "inheritance"
    symbols: List[str] = field(default_factory=list)
    file: str = ""


class CodeExtractor:
    """Extracts code structure and generates bottom-up blueprint."""
    
    def __init__(self, root: Path = Path(".")):
        self.root = root
        self.components: Dict[str, Component] = {}
        self.contracts: List[Contract] = []
        self.module_map: Dict[str, str] = {}  # file_path -> module_path
    
    def extract_project_structure(self, root: Path = None) -> Dict[str, Any]:
        """Extract entire project structure and generate blueprint."""
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
        """Find all Python files in the project."""
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
    
    def extract_file_structure(self, file_path: Path, root: Path = None) -> List[Component]:
        """
        Extract structure from a single file and return components.
        
        Args:
            file_path: Path to the file
            root: Project root (default: self.root)
            
        Returns:
            List of Component objects found in the file
        """
        if root is None:
            root = self.root
        
        components = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            # Calculate module path
            rel_path = file_path.relative_to(root)
            module_path = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            
            # Extract entities
            entities = self._identify_entities(tree, file_path, module_path)
            
            # Extract metadata
            for entity in entities:
                algorithm = self._extract_algorithm_from_code(tree, entity)
                if algorithm:
                    entity.algorithm = algorithm
                
                design_pattern = self._extract_design_pattern_from_structure(tree, entity, entities)
                if design_pattern:
                    entity.design_pattern = design_pattern
                
                complexity = self._analyze_complexity_from_code(tree, entity)
                if complexity:
                    entity.complexity = complexity
                
                components.append(entity)
        
        except Exception as e:
            # Return empty list if file can't be parsed
            pass
        
        return components
    
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
                
                # Analyze complexity
                complexity = self._analyze_complexity_from_code(tree, entity)
                if complexity:
                    entity.complexity = complexity
            
            # Extract relationships
            relationships = self._infer_relationships(tree, file_path, module_path, entities)
            
            # Store components
            for entity in entities:
                self.components[entity.id] = entity
            
            # Store contracts
            self.contracts.extend(relationships)
            
        except Exception as e:
            # Skip files that can't be parsed
            pass
    
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
        # Fallback to module-level entity
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
            
            # Check if multiple classes implement the same interface
            # (simplified check - would need more context in production)
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
            nonlocal max_nesting
            if isinstance(node, (ast.For, ast.While)):
                level += 1
                max_nesting = max(max_nesting, level)
            for child in ast.iter_child_nodes(node):
                count_nesting(child, level)
        
        count_nesting(entity_node)
        
        # Simple heuristics
        if max_nesting == 0:
            # No loops - could be O(1) or O(n) depending on operations
            # Check for recursion
            has_recursion = self._has_recursion(tree, entity)
            if has_recursion:
                return "O(n)"  # Conservative estimate
            return None  # Too uncertain
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
    
    def _generate_blueprint(self) -> Dict[str, Any]:
        """Generate blueprint.json from extracted components and contracts."""
        # Organize components by zone (simplified - can be enhanced)
        zones = {
            "client": [],
            "server": [],
            "data": []
        }
        
        # Convert components to blueprint format
        blueprint_components = []
        for comp in self.components.values():
            comp_dict = {
                "id": comp.id,
                "name": comp.name,
                "type": comp.type,
                "file": comp.file,
                "line": comp.line,
                "module_path": comp.module_path
            }
            
            if comp.methods:
                comp_dict["methods"] = comp.methods
            if comp.attributes:
                comp_dict["attributes"] = comp.attributes
            
            # Add metadata fields if present (only product logic, not methodology)
            # Note: methodology is excluded as it's a development methodology, not product logic
            if comp.algorithm:
                comp_dict["algorithm"] = comp.algorithm
            if comp.design_pattern:
                comp_dict["design_pattern"] = comp.design_pattern
            if comp.complexity:
                comp_dict["complexity"] = comp.complexity
            if comp.notes:
                comp_dict["notes"] = comp.notes
            
            blueprint_components.append(comp_dict)
            
            # Simple zone assignment (can be enhanced with heuristics)
            if "ui" in comp.module_path or "widget" in comp.module_path:
                zones["client"].append(comp.id)
            elif "core" in comp.module_path or "bridge" in comp.module_path:
                zones["server"].append(comp.id)
            else:
                zones["data"].append(comp.id)
        
        # Convert contracts to blueprint format
        blueprint_contracts = []
        for contract in self.contracts:
            contract_dict = {
                "from": contract.from_id,
                "to": contract.to_id,
                "type": contract.type,
                "file": contract.file
            }
            if contract.symbols:
                contract_dict["symbols"] = contract.symbols
            blueprint_contracts.append(contract_dict)
        
        from datetime import datetime
        
        return {
            "version": "1.0",
            "source": "code_extraction",
            "ground_truth": True,
            "last_updated": datetime.utcnow().isoformat(),
            "extraction_method": "ast_parsing",
            "zones": zones,
            "components": blueprint_components,
            "contracts": blueprint_contracts
        }
    
    def save_blueprint(self, blueprint: Dict[str, Any], output_path: Path) -> bool:
        """Save blueprint to file with metadata."""
        from manifest.audit.blueprint_metadata import save_blueprint_with_metadata
        return save_blueprint_with_metadata(
            blueprint, output_path, "code_extraction", True, "ast_parsing"
        )
