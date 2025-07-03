import google.generativeai as genai

# --- Configura tu API Key ---
genai.configure(api_key="AIzaSyD2Lb7u_x68AVNMskV_rrqjXl5mEwX1uH0")  # Reemplazá con tu API real

# --- Carga el modelo Gemini ---
model = genai.GenerativeModel("models/gemini-1.5-flash-latest")

# --- Texto previamente extraído por OCR ---
extraccion = """

CERVECERIA y MALTERIA QUILMES S.A.I.C.A y G.
CULT Sro
33-50835825-9
ING BRUTOS CONVMULTNrn, 902-868486-2
INICIO DE ACTIVIDADES 12/1959 IV.A. RESPONSABLE INSCRIPTO
DR.RAMON CARRILLO Y GRAL PAZ 1533
(C1437EGM) LA MATANZA
4630-0400/0500/0600
VENTA CTA.CTE.
Pzo Pago 7 dias
BULTOS
UNI
COD
DESCRIPCION
AY
MALTERIA
NOMBRE FANTASIA: WILLIAMSBURG
DOMICILIO: AVENIDA DEL LIBERTADOR 3883 CAPITAL FEDERAL CAPITAL FEDERAL C1425ABL
CONDICION DE VENTA:
CONDICION: IVA RES INSCRIP
C.U.I.T. 30716707527
Ingr.Brutos: 1587022-07
A
Código N° 01
Comunicate con nuestro
Centro de Experiencia de Cliente
11 6678 4173
0810 222 1234
¡Estamos para ayudarte!
CLIENTE: 453347 YARMAGA S.A.
P1.Ref: 607060426
FECHA VTO.: 08/07/25
FECHA: 1/07/25
NRO. 9407-06149867
REC.81030
CA.200800 VI. 1
FACTURA CTA.CTE
PRECIO UNI
PRECIO BRUTO
DESCUENTO
SUBTOTAL
%II
IMP.INTERNO
INT.NO GRAV.
IMP. IVA
TOTAL
PREC.UNI.FINAL
6.00
PACK
14933
ECO AND S/GAS 500x12 PET
16590.12
99540.72
39418.13
60122.59
4.17
1.00
PACK
3.00
PACK
30478
30481
3.00
PACK
30648
7UP FREE CAN 130 BUL/PAL 4X6 35
SEVEN-UP NF CAN 130 BUL/PAL 4X6
PEPSI CAN 4X6 354CC TITAN
24297.16
24297.16
12148.58
12148.58
4.17
2505.11
506.19
0.00
12625.74
75253.44
13469.13
0.00
2551.20
15205.97
16329.72
24297.16
72891.49
36445.75
36445.74
4.17
1518.57
0.00
7653.61
45617.92
16329.72
23448.54
70345.63
35172.82
35172.81
8.70
3058.51
0.00
7386.29
45617.61
16322.22
3.00
PACK
30793
1.00
1.00
1.00
PACK
UNID
UNID
SERVICIO LOGISTICO
PEPSI BLACK CAN 4X6 354CC TITAN
31074 PDT POMELO CAN 4X6 269CC 169 BU
40102 SERV BEES FLEX DELIVERY
99900
23448.54
70345.63
35172.82
35172.81
8.70
3058.51
0.00
7386.29
45617.61
16322.22
19219.67
19219.67
9609.85
15000.00
15000.00
3660.00
3660.00
0.00
0.00
8.70
9609.82
15000.00 16.28
3660.00 16.28
835.64
0.00
2018.06
12463.52
13378.54
2441.86
0.00
3150.00
20591.86
22088.37
595.81
0.00
768.60
5024.41
5389.56
SUBTOTAL
207332.35
14520.20
0.00
43539.79
265392.34
CABA RG987/12 %
Desc x VOL.ADIC.
6.00
GAS
13311.16
CZA
128549.82                                                                                                                                                      a Botella Quilmes. ****Ningún a
Programa Comercial "BEES - Ayudándote a crecer"
Recibido del 10 de octubre de 2012, la entrega de productos de la Familia Quilmes, Brahma y Andes se realizará prioritariamente contra la devolución de la Nueva
Williamsburg INFANTA
Fechai/25
Firma:
Aclaración
DMAN
SUBTOTAL
207332.35
INT NO GRAV
0.00
IMP.INTERNOS
14520.20
SUBTOTAL 2
265392.34
IVA INSC.
43539.79
IVA NO INSC.
06149867
Ref.:41548188
2409R-2865274
0.00
*Otros:
PERC.IN.BR.
13311.16
0.00
TOTAL BULTOS:
CAEA :35269899758002
SERVICIOS AL CLIENTE: -Lunes a Viernes: 8:00 a 18.00 hs. Sábados 8:30 a 13:30 hs.
POR FAVOR TENGA A MANO SU FACTURA CUANDO NOS LLAME. GRACIAS
ENVASES COMODATO No se transmite en ningún caso la propiedad de las botellas y cajones. Las botellas y cajones deberán ser devueltos en el momento
que la Compañía así lo exija y en el mismo estado en que
fueran entregados originariamente. No siendo así
, correrá por cuenta del tenedor el pago de su valor de
en
reposición a la fecha en que la Compañía lo requiera. No cambie nuestros envases
a terceros, son no negociables.
Hemos habilitado una línea telefónica gratuita, para que la utilicen quienes tengan denuncias y/o comentarios respecto del comportamiento ético de todos y cada uno
de los integrantes de la Compañía. Los
mensajes
,
que incluso podrán ser anónimos, serán escuchados exclusivamente
por
la
Gerencia de Auditoría General
Corporativa. Marcar 0800-288-5288 y luego 888-393-6831
COMPROBANTE: 1/2
Fecha Vto. : 15/07/25

"""

# --- Prompt para estructurar ese texto ---
prompt = """
Estás en rol de un Data Entry profesional. Vas a procesar la siguiente imagen de una factura gastronómica.
Las columnas deben estar en el siguiente orden exacto:
"Código Gem","Producto Gem","Cantidad Gem","Precio Gem,"Total Gem"

⚠ No modifiques la información del OCR.
(Las referencias de número de columna son dadas contando desde la primera de la izquierda, osea BULTOS sería la número 1.)
** Código Gem: Es la (columna 3) que se referencia como "COD". El contenido, osea los ID o Códigos puede variar un poco pero generalmente siguen un formato como: 14933, 31205, 99900, 31074. 
** Producto Gem: Corresponde a (la columna 4) "DESCRIPCION" de la factura, que indica detalle de cada producto.
** Cantidad Gem: Corresponde a los valores de la primer columna (Columna 1), es decir columna del OCR "BULTOS", la cual nos brinda información de cuantos kgs o unidades compramos. Ten en cuenta en este campo que, el proveedor indica de estas maneras: "1.0" para decir correctamente una unidad (1). No uses separador de miles, solo "," comas para separador de decimales.
** Precio Gem: Corresponde a la (columna 5) "PRECIO UNI" del OCR. Ten en cuenta que, el proveedor puede indicarnos de manera: "81704.32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
** Ejemplo de valores en Cantidad que se presentarán en las facturas: "40.0", Correcta transformacion: "40,0". Ej: "1.0", Correcta transofrmación: "1,0".
** Total Gem: Corresponde a la columna "SUBTOTAL" del OCR (columna 8). Ten en cuenta que, el proveedor puede indicarnos de manera: "81704,32" para informarnos de, (manera que corresponde) 81704,32. Es importante que incluyas las comas "," en los decimales. No incluyas separador de miles.
Es importante que el Total sea el valor de la columna "SUBTOTAL" del OCR ya que, necesitamos el subtotal con descuentos aplicados que es este.
El Total Gem, (Subtotal en OCR) corresponde al cuarto valor(numero) extraído por el OCR.
** No pueden haber códigos ni descripciones repetidas.
**Formato CSV válido:**
Prohibido agregar letras, texto, palabras antes o después del CSV. Solo necesito la tabla limpia con la información.
 No pongas ```csv ni ningun carácter fuera del CSV.
 Es importante que no pongas ```csv ni ``` ya que esto rompe el formato. Respeta. Solo CSV limpio.
- Todos los campos entre comillas dobles (").
- Separados por coma.
- Una línea por producto.
- Repetí la fecha si aparece solo una vez.
- No uses separadores de miles.
- Sin encabezado.
\"\"\"{}\"\"\"
""".format(extraccion)

# --- Solicitud a Gemini ---
try:
    response = model.generate_content(prompt)
    print("\n📋 Resultado estructurado:")
    print(response.text)
except Exception as e:
    print(f"❌ Error: {e}")
