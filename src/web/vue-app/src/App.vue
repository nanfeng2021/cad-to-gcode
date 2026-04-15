<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 导航栏 -->
    <nav class="bg-white shadow-sm border-b">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <h1 class="text-2xl font-bold text-primary">CAD to G-code</h1>
          </div>
          <div class="flex items-center space-x-4">
            <router-link to="/" class="text-gray-600 hover:text-primary px-3 py-2">首页</router-link>
            <router-link to="/upload" class="text-gray-600 hover:text-primary px-3 py-2">上传 DXF</router-link>
            <router-link to="/programs" class="text-gray-600 hover:text-primary px-3 py-2">程序管理</router-link>
            <router-link to="/settings" class="text-gray-600 hover:text-primary px-3 py-2">设置</router-link>
          </div>
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <router-view />
    </main>

    <!-- 页脚 -->
    <footer class="bg-white border-t mt-auto">
      <div class="max-w-7xl mx-auto px-4 py-4">
        <p class="text-center text-gray-500 text-sm">
          CAD to G-code Platform v0.2.0 | Powered by Hermes Agent
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup>
// 主应用组件
</script>
