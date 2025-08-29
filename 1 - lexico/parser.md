# Taller: Analizador Sintáctico

**Fecha de entrega:** 12 de septiembre<br>
**Duración estimada:** 1 semana

---

## 🎯 Objetivos

1. **Finalizar la construcción del AST (Árbol de Sintaxis Abstracta)**, incorporando los nodos que quedaron pendientes en la sesión anterior.
2. **Ampliar la gramática** para que reconozca:

- Estructuras de control **`WHILE`** y **`DO-WHILE`**.

3. **Extender la gramática** para soportar operadores **INC/DEC prefijos** (`++x`, `--x`).
4. **Recorrer el AST e imprimirlo** en consola utilizando la clase **`Tree`** de la librería rich.

---

## 📘 Instrucciones de Desarrollo

### 1. Revisión del AST existente

- Revisar los nodos ya implementados en `model.py`.
- Definir clases adicionales para representar:
  - `WhileStmt`
  - `DoWhileStmt`
  - `PreInc`
  - `PreDec`

### 2. Extensión de la gramática

Modificar el archivo del parser (`parser.py`) para incluir:

- **Producción de `while`**:
  ```bnf
  stmt : WHILE '(' expr ')' stmt
  ```

### 3. Integración con el AST

Cada una de las nuevas producciones debe generar un nodo del AST correspondiente. Ejemplo:

```python
@_("WHILE ‘(‘ expr ‘)’ stmt")
def while(self, p):
    Return WhileStmt(p.expr, p.stmt)
```

### 4. Visualización del AST

- Utilizar la clase Tree de rich para recorrer el AST.
- Implementar un método pretty() en cada nodo que:
  - Cree un sub-árbol.
  - Lo devuelva al árbol principal para impresión.

**Ejemplo de uso:**

```python
from rich.tree import Tree
print(ast.pretty())
```

## 📌 Actividades

### 1. Construcción de nodos AST

- Agregar las nuevas clases y asegurar consistencia con los nodos previos.

### 2. Extensión de la gramática

- Probar con fragmentos de código que incluyan while, do-while, ++x, –x.

### 3. Pruebas unitarias

- Verificar que el parser genere el AST esperado.
- Probar combinaciones de expresiones e instrucciones.

### 4. Visualización

- Ejecutar el recorrido e impresión del AST en consola.

## 📊 Criterios de Evaluación

| Criterio                                | Descripción                                                                                                     | Ponderación |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------- | :---------: |
| **Implementación del AST**              | Definición correcta de nodos (WhileStmt, DoWhileStmt, PreInc, PreDec) y su integración con los ya existentes.   |     30%     |
| **Gramática: WHILE y DO-WHILE**         | Reconocimiento correcto de las estructuras de control en la gramática y construcción adecuada de sus nodos AST. |     30%     |
| **Gramática: INC/DEC prefijos**         | Reconocimiento de operadores ++x, --x como expresiones válidas y su reflejo en el AST.                          |     20%     |
| **Visualización del AST con rich.Tree** | Implementación de recorridos pretty() y correcta impresión del árbol en consola.                                |     20%     |
| Total                                   |                                                                                                                 |    100%     |

## ✅ Entregables

- Código fuente actualizado del analizador sintáctico (parser.py, model.py).
- Un archivo de pruebas (test_parser.py) que muestre casos con while, do-while, ++x, --x.
- Capturas o salida en consola del AST impreso con rich.Tree.
