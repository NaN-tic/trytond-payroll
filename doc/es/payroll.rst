#:inside:company/human_resources:section:human_resources#

==========================================
Control de nóminas y contratos de empleado
==========================================

Dentro el menú **"Nóminas"** tenemos dos submenús que nos permiten controlar 
las nóminas, los contratos y reglas de los empleados:

- *Nóminas*: dónde llevamos a cabo la introducción y gestión de turnos de 
  trabajo, ausencias y derechos generados del empleado.
 
- *Contratos de empleado*: generaremos la información básica del contrato 
  laboral del empleado con datos como las horas anuales o el precio del turno 
  de trabajo.

Nóminas
=======

Al crear la nómina de un empleado tenemos que seleccionar el empleado y 
contrato (creado previamente), al cual pertenece la nómina y de que fecha es la 
nómina (normalmente será una mensualidad). A partir de aquí podremos añadirle 
*Líneas* con sus turnos de trabajo, derechos generados y pago de ausencias. 

La línea tendremos que clasificarla por "Tipo" y añadirle las "Horas de 
trabajo"; que junto con los tres campos indicados inicialmente nos permitarán 
componer toda la información laboral del empleado. Esta la podremos ver en la 
pestaña *Resumen*, dónde se nos mostrará la información de estas líneas agrupada 
en turnos de trabajo, ausencias y derechos generados. 

Al guardar las líneas de la nómina podremos ver los valores de las horas de 
trabajo, la clasificación de estas horas y el desglose. Para que 
posteriormente, cuando sea necesario, podamos facturar la nómina del empleado. 
Para ello seleccionaremos la opción *Facturar*, lo que nos creará una factura 
de proveedor. En este caso el destinatario (*Tercero*) de la factura será el 
empleado. 

Contratos de empleado
=====================

Para crear el contrato de un empleado, paso previo a crear la nómina del mismo, 
deberemos de indicar en que período tiene inicio este, las horas anuales que 
forman el contrato, las horas del turno de trabajo y el precio que tiene este. 

Una vez introducidos estos datos básicos, deberemos de añadirle un conjunto 
(grupo de empleados del que forma parte) al empleado, ya que cada conjunto 
tendrá unas reglas de nómina específicas. Los conjuntos de empleados y las 
reglas de estos los crearemos des del submenu **"Conjuntos de reglas del 
contrato de empleado"**. Al crear el grupo de empleados le añadiremos unas 
reglas a este conjunto. En cada regla deberemos seleccionar de forma 
obligatória el método de cálculo de esta regla; que podrá ser:

- *Turno de trabajo*: una agrupación de horas.
- *Intervenciones*: un caso o acción específica.

Además del método, deberemos introducir el *Tipo de hora* y el *Precio de 
coste* de esta. Opcionalmente podemos añadir también las *Horas* que conllevan 
realizar esta acción o turno (esto lo realizaremos en caso de saber que la 
regla conlleva un consumo fijo de horas). 

Una vez añadida toda la información guardaremos el contrato y el sistema nos 
generará el resumen de las horas por período. Estos períodos los determinamos 
en la configuración de las *Ausencias del empleado*.