# Fatos de engenharia de software verificados

⚠️ DIVERGÊNCIA DE DATA: uma fonte atribui o princípio de Liskov a 1987
(palestra "Data Abstraction and Hierarchy"), outra a 1993. As duas têm
parte da razão — Barbara Liskov apresentou a ideia na conferência de
1987, e a formulação formal saiu no artigo de 1994, com Jeannette Wing.
Os templates NÃO cobram a data, justamente por isso.

---

## Princípios SOLID

Sistematizados por Robert C. Martin.

| Sigla | Nome | Enunciado |
|---|---|---|
| S | Responsabilidade Única | uma classe deve ter um, e somente um, motivo para mudar |
| O | Aberto-Fechado | entidades devem estar abertas para extensão e fechadas para modificação |
| L | Substituição de Liskov | uma classe derivada deve poder substituir a classe base sem quebrar o programa |
| I | Segregação de Interface | clientes não devem ser forçados a depender de métodos que não usam |
| D | Inversão de Dependência | módulos de alto nível não devem depender de módulos de baixo nível; ambos dependem de abstrações |

⚠️ ARMADILHAS:
- O SRP fala em MOTIVO PARA MUDAR, não em "a classe faz uma coisa só".
  Uma classe pode ter vários métodos e ainda respeitar o princípio.
- O OCP pede EXTENSÃO sem MODIFICAÇÃO — herança ou composição, não
  edição do código existente.
- O DIP não é o mesmo que injeção de dependência: o DIP é o princípio;
  a injeção é uma técnica que ajuda a cumpri-lo.

Fontes: freeCodeCamp (O que é SOLID); Estratégia Concursos (TSE-TI);
Campus Code; Itaú Tech (Medium); Martin, Clean Architecture.

---

## Pilares da orientação a objetos

| Pilar | Definição |
|---|---|
| abstração | representar no código apenas os aspectos relevantes de uma entidade do mundo real, ocultando o que não interessa ao problema |
| encapsulamento | esconder o estado interno do objeto e expor apenas operações controladas de acesso |
| herança | permitir que uma classe reaproveite atributos e comportamentos de outra, estabelecendo relação "é um" |
| polimorfismo | permitir que um mesmo nome de operação produza comportamentos diferentes conforme o tipo do objeto |

⚠️ ARMADILHAS:
- Abstração e encapsulamento são confundidos: a ABSTRAÇÃO decide o que
  representar; o ENCAPSULAMENTO decide o que expor.
- Herança estabelece "é um"; composição estabelece "tem um". Preferir
  composição à herança é recomendação clássica.

---

## Padrões de projeto — categorias GoF

| Categoria | O que resolve | Exemplos |
|---|---|---|
| criacional | como os objetos são criados | Singleton, Factory Method, Builder, Prototype, Abstract Factory |
| estrutural | como as classes e objetos se compõem | Adapter, Decorator, Facade, Proxy, Composite, Bridge |
| comportamental | como os objetos se comunicam e distribuem responsabilidades | Observer, Strategy, Command, Template Method, Iterator, State |

Fonte: Gamma, Helm, Johnson e Vlissides — Design Patterns (1994).
