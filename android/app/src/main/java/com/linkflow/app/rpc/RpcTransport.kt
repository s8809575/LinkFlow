package com.linkflow.app.rpc

import org.json.JSONObject

interface RpcTransport {
    suspend fun invoke(method: String, params: JSONObject): JSONObject
}

