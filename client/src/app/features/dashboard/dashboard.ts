import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { Project, ProjectService } from '../../core/services/project.service';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  imports: [DatePipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  private projectService = inject(ProjectService);

  projects = signal<Project[]>([])
  selectedProject = signal<Project | null>(null);
  showCreateModal = signal(false);
  projectName = signal('');
  isButtonDisabled = computed(() => this.projectName().trim().length === 0);
  registeredEvents = signal<any[]>([])

  ngOnInit() {
    this.loadProjects();
  }

  loadProjects() {
    this.projectService.getProjects().subscribe(list => this.projects.set(list))
  }

  selectProject(project: Project) {
    this.selectedProject.set(project)
    this.loadEvents(project.id)
    this.refreshLogs()
  }

  onRegenerateKey() {
    const p = this.selectedProject();
    if (p && confirm('This will invalidate your old public key. Proceed?')) {
      this.projectService.regenerateKey(p.id).subscribe(updated => {
        this.selectedProject.set(updated);
        this.loadProjects();
      })
    }
  }

  onRegisterEvent(name: string) {
    const p = this.selectedProject();
    if (p && name) {
      this.projectService.registerEvent(p.id, name).subscribe({
        next: () => {
          alert('Event registered!');
          this.loadEvents(p.id);
        },
        error: (err) => alert(err.error?.detail || 'Failed to register event')
      });
    }
  }

  openModal() {
    this.projectName.set('');
    this.showCreateModal.set(true);
  }

  onCreateProject() {
    const name = this.projectName();
    this.projectService.createProject(name).subscribe({
      next: () => alert('Project Created'),
      error: (err) => alert(err.error.detail)
    });
    this.showCreateModal.set(false);
  }

  onAddDomain(newDomain: string) {
    const p = this.selectedProject();
    if (p && newDomain) {
      const currentDomains = p.allowed_origins || [];
      if (!currentDomains.includes(newDomain)) {
        const updatedDomains = [...currentDomains, newDomain];
        this.updateProjectWhitelist(p.id, updatedDomains);
      }
    }
  }

  onDeleteDomain(domainToRemove: string) {
    const p = this.selectedProject();
    if (p && p.allowed_origins) {
      const updatedDomains = p.allowed_origins.filter(d => d !== domainToRemove);
      this.updateProjectWhitelist(p.id, updatedDomains);
    }
  }

  private updateProjectWhitelist(id: string, domains: string[]) {
    this.projectService.updateWhitelist(id, domains).subscribe({
      next: (updated) => this.selectedProject.set(updated),
      error: (err) => alert(err.error?.detail || 'Update failed')
    });
  }

  loadEvents(projectId: string) {
    this.projectService.getRegisteredEvents(projectId).subscribe(events => {
      this.registeredEvents.set(events)
    })
  }

  onDeleteEvent(eventId: string) {
    const p = this.selectedProject();
    if (p && confirm('Delte this event type? Historic data will remain, but new event will be ignored.')) {
      this.projectService.deleteEvent(p.id, eventId).subscribe({
        next: () => {
          this.loadEvents(p.id);
          alert('Event deleted successfully.')
        },
        error: (err) => alert(err.error?.detail || "Failed to delete event")
      })
    }
  }

  refreshLogs() {
    const p = this.selectedProject();
    if (p) {
      this.projectService.getLiveFeed(p.id).subscribe(logs => this.liveLogs.set(logs));
    }
  }

  currentPage = signal(0);
  pageSize = 30;
  liveLogs = signal<any[]>([])

  loadMoreLogs() {
    const p = this.selectedProject();
    if (p) {
      const nextOffset = (this.currentPage() + 1)*this.pageSize;
      this.projectService.getLiveFeed(p.id, this.pageSize, nextOffset).subscribe(newLogs => {
        if (newLogs.length > 0) {
          this.liveLogs.update(currentLogs => [...currentLogs, ...newLogs]);
          this.currentPage.update(page => page + 1)
        } else {
          alert("No more logs aavilable")
        }
      })
    }
  }
}
