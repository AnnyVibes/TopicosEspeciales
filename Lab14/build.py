import json, copy
PROMPT = """=Analiza la siguiente solicitud de soporte:

{{ $json.ticket }}

Debes:
- identificar una categoría;
- asignar prioridad alta, media o baja;
- escribir un resumen de máximo 25 palabras;
- proponer una respuesta breve y profesional.

Reglas de prioridad:
- alta: cobros duplicados, fraude, seguridad, pérdida de dinero
  o servicio completamente bloqueado;
- media: problema funcional importante pero no crítico;
- baja: consulta general, información o mejora.

- No inventes información que no aparece en el ticket."""
SCHEMA = json.dumps({
 "type":"object",
 "properties":{
  "categoria":{"type":"string"},
  "prioridad":{"type":"string","enum":["alta","media","baja"]},
  "resumen":{"type":"string"},
  "respuesta_sugerida":{"type":"string"}},
 "required":["categoria","prioridad","resumen","respuesta_sugerida"]}, indent=2, ensure_ascii=False)

def setnode(name, id_, pos, fields):
    return {"parameters":{"assignments":{"assignments":[
              {"id":f"{id_}-{i}","name":k,"value":v,"type":"string"} for i,(k,v) in enumerate(fields)]},
              "includeOtherFields": True, "options":{}},
            "id":id_,"name":name,"type":"n8n-nodes-base.set","typeVersion":3.4,"position":pos}

def cond(id_, value):
    return {"conditions":{"options":{"caseSensitive":True,"leftValue":"","typeValidation":"strict","version":2},
            "conditions":[{"id":id_,"leftValue":"={{ $json.output.prioridad }}","rightValue":value,
            "operator":{"type":"string","operation":"equals"}}],"combinator":"and"},
            "renameOutput":True,"outputKey":value.upper()}

nodes = [
 {"parameters":{},"id":"n-trigger","name":"Manual Trigger","type":"n8n-nodes-base.manualTrigger","typeVersion":1,"position":[0,0]},
 setnode("Edit Fields (ticket)","n-ticket",[220,0],[("ticket","Me cobraron dos veces la mensualidad de mi cuenta y necesito resolverlo hoy porque el dinero se descontó de mi saldo.")]),
 {"parameters":{"promptType":"define","text":PROMPT,"hasOutputParser":True},
  "id":"n-chain","name":"Basic LLM Chain","type":"@n8n/n8n-nodes-langchain.chainLlm","typeVersion":1.5,"position":[440,0]},
 {"parameters":{"modelName":"models/gemini-2.5-flash","options":{"temperature":0}},
  "id":"n-model","name":"Google Gemini Chat Model","type":"@n8n/n8n-nodes-langchain.lmChatGoogleGemini","typeVersion":1,"position":[400,220]},
 {"parameters":{"schemaType":"manual","inputSchema":SCHEMA},
  "id":"n-parser","name":"Structured Output Parser","type":"@n8n/n8n-nodes-langchain.outputParserStructured","typeVersion":1.2,"position":[600,220]},
 {"parameters":{"rules":{"values":[cond("c-alta","alta")]},
   "options":{"fallbackOutput":"extra","renameFallbackOutput":"MEDIA / BAJA"}},
  "id":"n-switch","name":"Switch (prioridad)","type":"n8n-nodes-base.switch","typeVersion":3.2,"position":[800,0]},
 setnode("Escalar a humano","n-alta",[1060,-120],[("accion","ESCALAR A HUMANO"),("motivo","Ticket de alta prioridad detectado por IA")]),
 setnode("Respuesta normal","n-normal",[1060,120],[("accion","RESPUESTA NORMAL"),("motivo","El ticket puede continuar por el flujo estándar")]),
]
conns = {
 "Manual Trigger":{"main":[[{"node":"Edit Fields (ticket)","type":"main","index":0}]]},
 "Edit Fields (ticket)":{"main":[[{"node":"Basic LLM Chain","type":"main","index":0}]]},
 "Basic LLM Chain":{"main":[[{"node":"Switch (prioridad)","type":"main","index":0}]]},
 "Google Gemini Chat Model":{"ai_languageModel":[[{"node":"Basic LLM Chain","type":"ai_languageModel","index":0}]]},
 "Structured Output Parser":{"ai_outputParser":[[{"node":"Basic LLM Chain","type":"ai_outputParser","index":0}]]},
 "Switch (prioridad)":{"main":[[{"node":"Escalar a humano","type":"main","index":0}],[{"node":"Respuesta normal","type":"main","index":0}]]},
}
wf = {"name":"Clasificador IA de Soporte","nodes":nodes,"connections":conns,"settings":{"executionOrder":"v1"},"pinData":{}}
json.dump(wf, open("workflow_clasificador_ia_soporte.json","w"), indent=2, ensure_ascii=False)

# Variante Ollama (local)
wo = copy.deepcopy(wf); wo["name"]="Clasificador IA de Soporte (Ollama)"
for n in wo["nodes"]:
    if n["id"]=="n-model":
        n.update({"name":"Ollama Chat Model","type":"@n8n/n8n-nodes-langchain.lmChatOllama","typeVersion":1,
                  "parameters":{"model":"llama3.2:3b","options":{"temperature":0,"format":"json"}}})
wo["connections"]["Ollama Chat Model"]=wo["connections"].pop("Google Gemini Chat Model")
json.dump(wo, open("workflow_clasificador_ia_soporte_ollama.json","w"), indent=2, ensure_ascii=False)

# Reto 28: Form Trigger en vez de Manual Trigger
wr = copy.deepcopy(wf); wr["name"]="Clasificador IA de Soporte (Reto - Formulario)"
wr["nodes"][0] = {"parameters":{"formTitle":"Soporte - Nueva solicitud","formDescription":"Describe tu problema. Usa solo datos ficticios.",
  "formFields":{"values":[{"fieldLabel":"ticket","fieldType":"textarea","requiredField":True}]},"options":{}},
  "id":"n-form","name":"Formulario de soporte","type":"n8n-nodes-base.formTrigger","typeVersion":2.2,"position":[0,0],"webhookId":"clasificador-ia-soporte"}
wr["nodes"][1] = setnode("Edit Fields (ticket)","n-ticket",[220,0],[("ticket","={{ $json.ticket }}")])
wr["connections"]["Formulario de soporte"]=wr["connections"].pop("Manual Trigger")
json.dump(wr, open("workflow_reto_form_trigger.json","w"), indent=2, ensure_ascii=False)
print("ok")
