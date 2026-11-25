<script setup lang="ts">
defineProps<{ body: string; title: string }>();
</script>

<template>
  <article>
    <h2>{{ title }}</h2>
    <div class="body" v-html="body"></div>
  </article>
</template>
