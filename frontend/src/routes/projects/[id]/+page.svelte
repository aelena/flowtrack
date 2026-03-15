<script>
  import { page } from '$app/stores';
  import ProjectView from '$lib/components/ProjectView.svelte';

  $: projectId = $page.params.id;
</script>

<ProjectView {projectId} />
