<template>
  <div class="space-y-6">
    <h2 class="text-2xl font-bold text-gray-800">系统设置</h2>

    <!-- 加工参数设置 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">默认加工参数</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">默认材料</label>
          <select v-model="settings.defaultMaterial" class="w-full border rounded px-3 py-2">
            <option value="45#钢">45#钢</option>
            <option value="40Cr">40Cr</option>
            <option value="不锈钢">不锈钢</option>
            <option value="铝合金">铝合金</option>
            <option value="黄铜">黄铜</option>
          </select>
        </div>
        
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">默认数控系统</label>
          <select v-model="settings.defaultMachine" class="w-full border rounded px-3 py-2">
            <option value="FANUC">FANUC</option>
            <option value="Siemens">Siemens</option>
            <option value="Mitsubishi">Mitsubishi</option>
            <option value="GSK">GSK</option>
            <option value="HNC">HNC</option>
          </select>
        </div>
      </div>
      
      <button @click="saveSettings" class="mt-4 px-6 py-2 bg-primary text-white rounded hover:bg-blue-600">
        保存设置
      </button>
    </div>

    <!-- API 配置 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">API 配置</h3>
      <div class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">API 地址</label>
          <input v-model="settings.apiUrl" type="text" class="w-full border rounded px-3 py-2" />
        </div>
        <div class="flex items-center">
          <input v-model="settings.autoSave" type="checkbox" class="mr-2" />
          <label class="text-sm text-gray-700">自动生成后保存到数据库</label>
        </div>
      </div>
    </div>

    <!-- 关于信息 -->
    <div class="bg-white rounded-lg shadow p-6">
      <h3 class="text-lg font-semibold mb-4">关于</h3>
      <div class="space-y-2 text-sm text-gray-600">
        <div><strong>版本:</strong> v0.2.0</div>
        <div><strong>技术栈:</strong> Vue 3 + TailwindCSS + FastAPI</div>
        <div><strong>支持格式:</strong> DXF R12-R2018</div>
        <div><strong>识别特征:</strong> 外圆、锥面、圆弧、槽、螺纹等 7 种</div>
        <div><strong>支持材料:</strong> 45#钢、40Cr、不锈钢、铝合金、黄铜</div>
        <div><strong>数控系统:</strong> FANUC、Siemens、Mitsubishi、GSK、HNC</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const settings = ref({
  defaultMaterial: '45#钢',
  defaultMachine: 'FANUC',
  apiUrl: '/api',
  autoSave: true,
})

onMounted(() => {
  // 从 localStorage 加载设置
  const saved = localStorage.getItem('cad2gcode_settings')
  if (saved) {
    settings.value = JSON.parse(saved)
  }
})

const saveSettings = () => {
  localStorage.setItem('cad2gcode_settings', JSON.stringify(settings.value))
  alert('设置已保存')
}
</script>
