# Add-on: Laravel (PHP)

Apply everything below unless the user asks otherwise.

## Method
- Change only what the task needs; runnable code with imports, no `...`; for edits show the diff + command.

## Routing & controllers
- `routes/web.php` (Blade) or `routes/api.php` (JSON); name routes, `route('users.show')`.
- `Route::middleware([...])->prefix('admin')->group(...)`; `{user}` -> `User $user`.
- Controllers `--resource`: thin; inject `Request`/`FormRequest`; return `view()`, `redirect()` or JSON.

## Eloquent ORM
- Models extend `Model`; set `$fillable`. `hasMany`/`belongsTo`; eager load `with('posts')` against N+1.
- `User::where(...)->paginate(15)`, `firstOrCreate`, `updateOrCreate`, `firstOrFail`.

## Migrations
- `make:migration create_users_table --create=users`; `$table->string('name'); $table->foreignId('user_id')->constrained(); $table->timestamps();`
- Keep `up()`/`down()` symmetric; never edit a run migration. `migrate`.

## Validation
- `make:request StoreUserRequest`: `authorize(): bool`, `rules()` with `'email' => ['required','unique:users,email']`.
- Or `$request->validate([...])`; update `Rule::unique('users')->ignore($user)`; errors use `$errors`.

## Middleware
- `make:middleware EnsureAdmin`; act before `return $next($request)`. Register in `bootstrap/app.php` (11+), else `Kernel.php`.
- Built-ins: `auth`, `guest`, `verified`, `can:policy,model`, `throttle:60,1`.

## Blade
- `@extends`/`@section` or `<x-layout>`. `{{ $var }}` escapes; `{!! !!}` is raw (trusted only).
- `@if`, `@foreach`, `@csrf`, `@method('PUT')`, `@auth`, `@can`; `old()`, `@error`.

## Artisan
- `make:model Post -mfc`, `make:seeder`; `route:list`, `migrate:fresh --seed` (dev), `config:cache`, `tinker`, `queue:work`.

## Service providers
- `make:provider PaymentServiceProvider`; bind `$this->app->bind(Contract::class, Impl::class)` in `register()`, events in `boot()`.
- Register in `bootstrap/providers.php` (11+). Config via `config('services.key')`, `env()` only in config.
